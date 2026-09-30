import asyncio
import json
import logging

import openai
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dialogue import Turn, infer_intent, resolve_stage, search_query_for_turn
from app.core.execution import (
    build_memory_context,
    build_system_prompt,
    generate_dealer_reply,
    interpret_turn,
    should_store_memory,
    summarise_exchange,
)
from app.core.generate import generate_embedding
from app.core.prompts import FALLBACK_REPLY, GREETING
from app.models.conversation import Conversation, Message, MessageRole
from app.models.user import User
from app.schema.api import APIPaginationFilter
from app.schema.conversation import ConversationPaginationFilter
from app.services.catalog import CatalogError, format_offers, get_catalog

logger = logging.getLogger(__name__)


async def get_conversation_list(
    db: AsyncSession, user: User, filters: ConversationPaginationFilter
) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.user),
            selectinload(Conversation.last_message),
        )
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .offset((filters.page - 1) * filters.limit)
        .limit(filters.limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_conversation_count(
    db: AsyncSession, user_id: int, filters: ConversationPaginationFilter
) -> int:
    stmt = select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def create_single_conversation(db: AsyncSession, user_id: int) -> Conversation:
    """Start a chat and store the opening question as the first assistant message."""
    conversation = Conversation(user_id=user_id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    greeting = await create_single_message(
        db, conversation.id, MessageRole.ASSISTANT, GREETING
    )
    await update_conversation_last_message(db, conversation.id, greeting.id)
    return conversation


async def update_conversation_last_message(
    db: AsyncSession, conversation_id: int, last_message_id: int
) -> None:
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(last_message_id=last_message_id)
    )
    await db.commit()


async def delete_single_conversation(db: AsyncSession, conversation_id: int) -> None:
    await db.execute(delete(Conversation).where(Conversation.id == conversation_id))
    await db.commit()


async def get_single_conversation(
    db: AsyncSession, conversation_id: int
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def create_single_message(
    db: AsyncSession,
    conversation_id: int,
    role: MessageRole,
    content: str,
    memory_text: str | None = None,
    embedding_768: list[float] | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role.value,
        content=content,
        memory_text=memory_text,
        embedding_768=embedding_768,
        is_embedded=embedding_768 is not None,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_message_list(
    db: AsyncSession, conversation_id: int, filters: APIPaginationFilter
) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .where(Message.role.in_(["user", "assistant"]))
        .order_by(Message.created_at.desc())
        .offset((filters.page - 1) * filters.limit)
        .limit(filters.limit)
    )
    return result.scalars().all()


async def get_message_count(db: AsyncSession, conversation_id: int) -> int:
    result = await db.execute(
        select(func.count(Message.id))
        .where(Message.conversation_id == conversation_id)
        .where(Message.role.in_(["user", "assistant"]))
    )
    return result.scalar_one()


async def get_conversation_related_messages(
    db: AsyncSession, conversation_id: int, query_embedding: list[float], limit: int = 3
) -> list[dict]:
    distance = Message.embedding_768.cosine_distance(query_embedding)
    result = await db.execute(
        select(
            Message.memory_text,
            (1 - distance).label("similarity"),
        )
        .where(
            Message.conversation_id == conversation_id,
            Message.role == "memory",
            Message.is_embedded.is_(True),
            Message.embedding_768.isnot(None),
        )
        .order_by(distance)
        .limit(limit)
    )
    return result.mappings().all()


async def store_memory(
    db: AsyncSession, conversation_id: int, user_message: str, answer: str
) -> None:
    """Summarise the exchange and store it as an embedded memory row."""
    await asyncio.sleep(10)
    try:
        if should_store_memory(user_message, answer):
            logger.info("User message worth storing as memory")
            raw_exchange = f"Customer said: {user_message}\nAgent replied: {answer}"
            summary = summarise_exchange(user_message, answer)
            logger.info("User message is summarised")

            embedding = generate_embedding(summary)
            await create_single_message(
                db,
                conversation_id,
                MessageRole.MEMORY,
                raw_exchange,
                summary,
                embedding,
            )
            logger.info("New Memory created")
    except openai.APIError:
        logger.exception("Failed to store memory for conversation %s", conversation_id)


async def process_user_message(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    username: str,
    conversation_id: int,
    user_message: str,
) -> Message:
    """Look up the catalog, ask the model for a reply, and store both turns."""
    recent_history = await get_message_list(
        db=db,
        conversation_id=conversation_id,
        filters=APIPaginationFilter(page=1, limit=50),
    )
    history = [
        {"role": message.role, "content": message.content}
        for message in reversed(recent_history)
    ]
    logger.info("Found top %s messages in the conversation", len(history))

    try:
        catalog = get_catalog()
    except CatalogError as exc:
        logger.error("Car catalog unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The car catalog is unavailable.",
        ) from exc

    try:
        parsed = interpret_turn(user_message, history)
        turn = Turn(
            parsed.car_query,
            parsed.option,
            parsed.slot,
            infer_intent(user_message, parsed.intent),
        )
        logger.info(
            "Interpreted turn car_query=%s option=%s slot=%s intent=%s",
            turn.car_query,
            turn.option,
            turn.slot,
            turn.intent,
        )
        search_result = catalog.search(
            search_query_for_turn(turn, user_message, history)
        )
        stage = resolve_stage(turn, search_result)
        reveal_contact = stage.value in {"dealer_details", "confirm_call"}
        catalog_context = format_offers(
            search_result,
            include_phone=reveal_contact,
            include_address=stage.value == "dealer_details",
        )
        logger.info(
            "Dialogue stage %s with %s catalog hits", stage.value, search_result.total
        )

        query_embedding = generate_embedding(user_message)
        memory_rows = await get_conversation_related_messages(
            db=db,
            conversation_id=conversation_id,
            query_embedding=query_embedding,
            limit=3,
        )
        logger.info("Found %s related memories for the conversation", len(memory_rows))
        memory_context = build_memory_context(memory_rows)

        system_prompt = build_system_prompt(
            username=username,
            inventory=catalog.inventory_summary(),
            catalog_context=catalog_context,
            stage=stage.value,
            memory_context=memory_context,
        )
        answer = generate_dealer_reply(
            system_prompt=system_prompt,
            user_message=user_message,
            recent_history=history,
        )
    except openai.APIError:
        logger.exception("Model request failed for conversation %s", conversation_id)
        answer = FALLBACK_REPLY

    if not answer:
        answer = FALLBACK_REPLY

    await create_single_message(db, conversation_id, MessageRole.USER, user_message)
    assistant_message = await create_single_message(
        db, conversation_id, MessageRole.ASSISTANT, answer
    )
    logger.info("Assistant message created for conversation %s", conversation_id)

    if answer != FALLBACK_REPLY:
        background_tasks.add_task(
            store_memory, db, conversation_id, user_message, answer
        )

    logger.info(
        json.dumps(
            {
                "message": "User message processed successfully",
                "conversation_id": conversation_id,
                "answer": answer,
            }
        )
    )

    await update_conversation_last_message(db, conversation_id, assistant_message.id)
    return assistant_message
