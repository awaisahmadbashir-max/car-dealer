"""LLM calls for the car dealer assistant.

Catalog lookup stays outside this module. The model extracts what the shopper
means, then writes the reply from the facts it is given.
"""

import logging

import openai

from app.configs import settings
from app.core.client import openai_client
from app.core.decorators import with_retry
from app.core.dialogue import Turn, parse_turn_text
from app.core.prompts import (
    MEMORY_CLASSIFIER_PROMPT,
    STAGE_INSTRUCTIONS,
    SUMMARISE_MEMORY_PROMPT,
    SYSTEM_PROMPT,
    TURN_EXTRACT_PROMPT,
)

logger = logging.getLogger(__name__)


@with_retry(
    retryable_exceptions=(openai.RateLimitError, openai.APIError),
    max_retries=2,
    base_delay=2.0,
)
def should_store_memory(user_message: str, answer: str) -> bool:
    """Ask the model whether this exchange is worth remembering."""
    if not user_message.strip() or not (answer or "").strip():
        return False

    response = openai_client.chat.completions.create(
        model=settings.MODEL_CHAT_NAME,
        messages=[
            {"role": "system", "content": MEMORY_CLASSIFIER_PROMPT},
            {
                "role": "user",
                "content": f"Customer: {user_message}\n\nAgent: {answer}",
            },
        ],
        temperature=0.0,
        max_tokens=5,
    )
    verdict = (response.choices[0].message.content or "").strip().lower()
    logger.info("Memory classifier verdict: %s", verdict)
    return verdict.startswith("yes")


@with_retry(
    retryable_exceptions=(openai.RateLimitError, openai.APIError),
    max_retries=3,
    base_delay=1.0,
)
def summarise_exchange(user_message: str, answer: str) -> str:
    """Compress one exchange into a short memory."""
    response = openai_client.chat.completions.create(
        model=settings.MODEL_CHAT_NAME,
        messages=[
            {"role": "system", "content": SUMMARISE_MEMORY_PROMPT},
            {
                "role": "user",
                "content": f"Customer: {user_message}\n\nAgent: {answer}",
            },
        ],
        temperature=0.0,
        max_tokens=300,
    )
    return (response.choices[0].message.content or "").strip()


@with_retry(
    retryable_exceptions=(openai.RateLimitError, openai.APIError),
    max_retries=2,
    base_delay=1.0,
)
def interpret_turn(user_message: str, recent_history: list[dict]) -> Turn:
    """Read the chat and return the car, option, and time slot."""
    response = openai_client.chat.completions.create(
        model=settings.MODEL_CHAT_NAME,
        messages=[
            {"role": "system", "content": TURN_EXTRACT_PROMPT},
            *recent_history,
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
        max_tokens=200,
    )
    raw = response.choices[0].message.content or ""
    logger.info("Turn extraction raw response: %s", raw)
    return parse_turn_text(raw, fallback_query=user_message)


def build_memory_context(memory_rows: list[dict]) -> str | None:
    """Join retrieved memories into a prompt block."""
    if not memory_rows:
        return None
    lines = [f"- {row['memory_text']}" for row in memory_rows]
    return "\n".join(lines)


def build_system_prompt(
    username: str,
    inventory: str,
    catalog_context: str,
    stage: str,
    memory_context: str | None,
) -> str:
    """Fill the dealer-assistant prompt with this turn's facts."""
    return SYSTEM_PROMPT.format(
        username=username,
        stage=stage,
        stage_instruction=STAGE_INSTRUCTIONS[stage],
        catalog_context=catalog_context,
        inventory=inventory,
        memory_context=memory_context or "None yet.",
    ).strip()


@with_retry(
    retryable_exceptions=(openai.RateLimitError, openai.APIError),
    max_retries=3,
    base_delay=1.0,
)
def generate_dealer_reply(
    system_prompt: str,
    user_message: str,
    recent_history: list[dict],
) -> str:
    """Write the shopper-facing reply from the system prompt and recent chat."""
    messages = [
        {"role": "system", "content": system_prompt},
        *recent_history,
        {"role": "user", "content": user_message},
    ]

    response = openai_client.chat.completions.create(
        model=settings.MODEL_CHAT_NAME,
        messages=messages,
        temperature=0.2,
    )

    return (response.choices[0].message.content or "").strip()
