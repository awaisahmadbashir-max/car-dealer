from app.core.dialogue import (
    Stage,
    Turn,
    infer_intent,
    parse_turn_text,
    resolve_stage,
    search_query_for_turn,
)
from app.services.catalog import Car, CarOffer, Dealer, SearchResult


def _result(**overrides) -> SearchResult:
    defaults = dict(
        query="toyota corolla",
        matches=[],
        total=0,
        truncated=False,
        too_broad=False,
        suggestions=[],
    )
    defaults.update(overrides)
    return SearchResult(**defaults)


def _offer() -> CarOffer:
    car = Car(
        id=1,
        make="Toyota",
        model="Corolla",
        variant="Altis Grande 1.8",
        price=9250000,
        dealer_id=1,
    )
    dealer = Dealer(
        id=1,
        name="Crown Toyota",
        phone="0300-4112201",
        email="sales@crowntoyota.example",
        city="Karachi",
        address="12 Shahrah-e-Faisal",
    )
    return CarOffer(car=car, dealer=dealer)


def test_parse_turn_reads_json_and_option_aliases() -> None:
    turn = parse_turn_text(
        '```json\n{"car_query": "Toyota Corolla", "option": "2", "slot": "Friday at 3pm"}\n```'
    )
    assert turn == Turn(car_query="Toyota Corolla", option="call", slot="Friday at 3pm")


def test_parse_turn_falls_back_when_json_is_invalid() -> None:
    turn = parse_turn_text("not json", fallback_query="Honda Civic")
    assert turn.car_query == "Honda Civic"
    assert turn.option is None
    assert turn.slot is None


def test_unknown_car_asks_for_another() -> None:
    stage = resolve_stage(
        Turn(car_query="BMW X5", option=None, slot=None),
        _result(query="bmw x5"),
    )
    assert stage is Stage.NOT_FOUND


def test_several_matches_ask_the_shopper_to_choose() -> None:
    stage = resolve_stage(
        Turn(car_query="Toyota Corolla", option=None, slot=None),
        _result(matches=[_offer(), _offer()], total=2),
    )
    assert stage is Stage.CHOOSE_CAR


def test_one_match_offers_details_or_a_call() -> None:
    stage = resolve_stage(
        Turn(car_query="Toyota Corolla Altis Grande 1.8", option=None, slot=None),
        _result(matches=[_offer()], total=1),
    )
    assert stage is Stage.OFFER_NEXT


def test_dealer_details_require_one_car() -> None:
    one = resolve_stage(
        Turn(car_query="Toyota Corolla", option="details", slot=None),
        _result(matches=[_offer()], total=1),
    )
    many = resolve_stage(
        Turn(car_query="Toyota Corolla", option="details", slot=None),
        _result(matches=[_offer(), _offer()], total=2),
    )
    assert one is Stage.DEALER_DETAILS
    assert many is Stage.NEED_ONE_CAR


def test_call_asks_for_a_slot_then_confirms() -> None:
    focused = _result(matches=[_offer()], total=1)
    ask = resolve_stage(
        Turn(car_query="Toyota Corolla", option="call", slot=None), focused
    )
    confirm = resolve_stage(
        Turn(car_query="Toyota Corolla", option="call", slot="Friday at 3pm"),
        focused,
    )
    assert ask is Stage.ASK_SLOT
    assert confirm is Stage.CONFIRM_CALL


def test_make_only_stays_broad() -> None:
    stage = resolve_stage(
        Turn(car_query="Toyota", option=None, slot=None),
        _result(query="toyota", too_broad=True, suggestions=["Toyota Corolla"]),
    )
    assert stage is Stage.TOO_BROAD


def test_feature_question_does_not_lock_onto_one_listing() -> None:
    message = "what features they provide with so i can choose a specific one"
    turn = Turn(
        car_query="Toyota Hilux Revo V AT",
        option=None,
        slot=None,
        intent=infer_intent(message, "choose"),
    )
    history = [
        {"role": "user", "content": "I am confused about Haval, Honda and Toyota"},
        {"role": "assistant", "content": "We have H6, Civic, Corolla, and Hilux."},
    ]
    assert turn.intent == "features"
    assert resolve_stage(turn, _result(matches=[_offer()], total=1)) is Stage.FEATURES
    assert search_query_for_turn(turn, message, history) == (
        "I am confused about Haval, Honda and Toyota"
    )


def test_rejection_drops_the_suggested_car() -> None:
    message = "why are you recommending me Hilux Revo specifically then?"
    turn = Turn(
        car_query="Toyota Hilux Revo",
        option=None,
        slot=None,
        intent=infer_intent(message, None),
    )
    history = [
        {"role": "user", "content": "Haval, Honda and Toyota"},
        {
            "role": "assistant",
            "content": "Toyota Hilux Revo V AT, sold by Pearl Toyota",
        },
        {
            "role": "user",
            "content": "why are you recommending me Hilux Revo specifically then?",
        },
    ]
    assert turn.intent == "reject"
    assert resolve_stage(turn, _result(matches=[_offer(), _offer()], total=2)) is (
        Stage.RESET
    )
    assert search_query_for_turn(turn, message, history) == "Haval, Honda and Toyota"


def test_no_car_yet_asks_what_they_want() -> None:
    stage = resolve_stage(
        Turn(car_query=None, option=None, slot=None),
        _result(query=""),
    )
    assert stage is Stage.ASK_CAR
