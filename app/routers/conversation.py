import logging
from typing import Annotated

from fastapi import BackgroundTasks, HTTPException, Query, status
from fastapi.routing import APIRouter

from app.dependencies.auth import AuthUserDependency
from app.dependencies.db import DBDependency
from app.schema.api import APIPaginatedResponse, APIPaginationFilter, APIResponse
from app.schema.conversation import (
    ConversationPaginationFilter,
    ConversationSchema,
    CreateMessageSchema,
    MessageSchema,
)
from app.services.conversation import (
    create_single_conversation,
    delete_single_conversation,
    get_conversation_count,
    get_conversation_list,
    get_message_count,
    get_message_list,
    get_single_conversation,
    process_user_message,
)

logger = logging.getLogger(__name__)

conversation_router = APIRouter(prefix="/conversation", tags=["conversation"])


@conversation_router.get("/")
async def get_conversations(
    db: DBDependency,
    user: AuthUserDependency,
    filters: Annotated[ConversationPaginationFilter, Query()],
) -> APIPaginatedResponse:
    conversations = await get_conversation_list(db, user, filters)
    total_items = await get_conversation_count(db, user.id, filters)

    return APIPaginatedResponse(
        page=filters.page,
        limit=filters.limit,
        total_items=total_items,
        data=[
            ConversationSchema.model_validate(conversation)
            for conversation in conversations
        ],
    )


@conversation_router.get("/{id}/message")
async def get_messages(
    db: DBDependency,
    user: AuthUserDependency,
    id: int,
    filters: Annotated[APIPaginationFilter, Query()],
) -> APIPaginatedResponse:
    conversation = await get_single_conversation(db, id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    messages = await get_message_list(db, id, filters)
    total_items = await get_message_count(db, id)

    return APIPaginatedResponse(
        page=filters.page,
        limit=filters.limit,
        total_items=total_items,
        data=[MessageSchema.model_validate(message) for message in messages],
    )


@conversation_router.post("/message")
async def create_message(
    db: DBDependency,
    background_tasks: BackgroundTasks,
    user: AuthUserDependency,
    body: CreateMessageSchema,
) -> APIResponse:
    conversation_id = body.conversation_id
    created_now = conversation_id is None
    if created_now:
        conversation = await create_single_conversation(db=db, user_id=user.id)
        conversation_id = conversation.id
    else:
        conversation = await get_single_conversation(db, conversation_id)
        if conversation is None or conversation.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

    try:
        assistant_message = await process_user_message(
            db=db,
            background_tasks=background_tasks,
            username=user.full_name,
            conversation_id=conversation_id,
            user_message=body.content,
        )
    except HTTPException:
        if created_now:
            await delete_single_conversation(db, conversation_id)
        raise
    except Exception as exc:
        logger.exception("Error processing user message")
        if created_now:
            await delete_single_conversation(db, conversation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not reply just now. Please try again.",
        ) from exc

    return APIResponse(
        detail="Message created",
        data=MessageSchema.model_validate(assistant_message),
    )
