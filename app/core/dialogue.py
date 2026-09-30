"""Decide the next step in the car-shopping conversation.

The model extracts a car phrase, an option, and a time slot. This module turns
those fields plus the catalog search into one stage so the reply stays on the
script even when the wording varies.
"""

import json
import re
from dataclasses import dataclass
from enum import Enum

from app.services.catalog import SearchResult


class Stage(Enum):
    ASK_CAR = "ask_car"
    NOT_FOUND = "not_found"
    TOO_BROAD = "too_broad"
    CHOOSE_CAR = "choose_car"
    OFFER_NEXT = "offer_next"
    DEALER_DETAILS = "dealer_details"
    ASK_SLOT = "ask_slot"
    CONFIRM_CALL = "confirm_call"
    NEED_ONE_CAR = "need_one_car"
    FEATURES = "features"
    RESET = "reset"


@dataclass(frozen=True)
class Turn:
    """What the shopper just asked for, extracted from the chat."""

    car_query: str | None
    option: str | None
    slot: str | None
    intent: str | None = None


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _option(value: object) -> str | None:
    text = _clean(value)
    if text is None:
        return None
    normalized = text.lower()
    if normalized in {"details", "dealer", "dealer_details", "1"}:
        return "details"
    if normalized in {"call", "schedule", "schedule_call", "2"}:
        return "call"
    return None


def parse_turn_payload(payload: object) -> Turn:
    """Build a turn from a decoded JSON object."""
    if not isinstance(payload, dict):
        return Turn(car_query=None, option=None, slot=None)
    return Turn(
        car_query=_clean(payload.get("car_query")),
        option=_option(payload.get("option")),
        slot=_clean(payload.get("slot")),
        intent=_intent(payload.get("intent")),
    )


def _intent(value: object) -> str | None:
    text = _clean(value)
    if text is None:
        return None
    normalized = text.lower()
    if normalized in {"features", "reject", "choose", "browse"}:
        return normalized
    return None


def infer_intent(user_message: str, intent: str | None) -> str | None:
    """Prefer the shopper's words when they ask for specs or reject a suggestion."""
    lowered = user_message.lower()
    if any(
        word in lowered
        for word in ("feature", "features", "specs", "specifications", "mileage")
    ):
        return "features"
    if any(
        phrase in lowered
        for phrase in (
            "why are you",
            "did not you",
            "didn't you",
            "don't have",
            "do not have",
            "excuse",
            "recommending",
            "you said you have",
        )
    ):
        return "reject"
    return intent


def search_query_for_turn(
    turn: Turn, user_message: str, history: list[dict]
) -> str | None:
    """Search cars the shopper named, not a listing the assistant invented.

    Feature questions and rejections use earlier shopper messages only, so a
    car mentioned while objecting to it does not become the new search.
    """
    earlier = [
        message["content"] for message in history if message.get("role") == "user"
    ]
    if turn.intent in {"features", "reject"}:
        kept = [
            text
            for text in earlier
            if infer_intent(text, None) not in {"features", "reject"}
        ]
        text = " ".join(kept).strip()
        return text or None
    if _accepts_suggestion(user_message) and turn.car_query:
        return turn.car_query
    text = " ".join([*earlier, user_message]).strip()
    return text or None


def _accepts_suggestion(user_message: str) -> bool:
    return bool(
        re.match(
            r"^\s*(yes|yeah|yep|ok|okay|sure|that one|the first|go with (it|that)|i'?ll take)\b",
            user_message.strip(),
            flags=re.IGNORECASE,
        )
    )


def parse_turn_text(raw: str, fallback_query: str | None = None) -> Turn:
    """Parse the model's JSON. On invalid JSON, search the shopper's own words."""
    text = raw.strip()
    fenced = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(0)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        query = _clean(fallback_query)
        return Turn(car_query=query, option=None, slot=None)
    return parse_turn_payload(payload)


def _one_focused_car(result: SearchResult) -> bool:
    return len(result.matches) == 1 and not result.truncated and not result.too_broad


def _several_cars(result: SearchResult) -> bool:
    return result.truncated or len(result.matches) > 1 or result.too_broad


def resolve_stage(turn: Turn, result: SearchResult) -> Stage:
    """Pick the next dialogue step from the extracted turn and catalog hits."""
    if turn.intent == "features":
        return Stage.FEATURES
    if turn.intent == "reject":
        return Stage.RESET

    focused = _one_focused_car(result)
    several = _several_cars(result)

    if turn.option == "details":
        if focused:
            return Stage.DEALER_DETAILS
        if several:
            return Stage.NEED_ONE_CAR
        return Stage.ASK_CAR if not turn.car_query else Stage.NOT_FOUND

    if turn.option == "call":
        if not focused:
            if several:
                return Stage.NEED_ONE_CAR
            return Stage.ASK_CAR if not turn.car_query else Stage.NOT_FOUND
        if not turn.slot:
            return Stage.ASK_SLOT
        return Stage.CONFIRM_CALL

    if result.too_broad:
        return Stage.TOO_BROAD
    if len(result.matches) > 1 or result.truncated:
        return Stage.CHOOSE_CAR
    if focused:
        return Stage.OFFER_NEXT
    if turn.car_query:
        return Stage.NOT_FOUND
    return Stage.ASK_CAR
