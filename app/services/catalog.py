"""Load cars and dealers from CSV and match a shopper's request to them."""

import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CAR_COLUMNS = ("id", "make", "model", "variant", "price", "dealer_id")
DEALER_COLUMNS = ("id", "name", "phone", "email", "city", "address")
LISTING_LIMIT = 8


class CatalogError(Exception):
    """The car catalog could not be read."""


@dataclass(frozen=True)
class Dealer:
    id: int
    name: str
    phone: str
    email: str
    city: str
    address: str


@dataclass(frozen=True)
class Car:
    id: int
    make: str
    model: str
    variant: str
    price: int
    dealer_id: int


@dataclass(frozen=True)
class CarOffer:
    car: Car
    dealer: Dealer | None


@dataclass(frozen=True)
class SearchResult:
    """Matches for one shopper query.

    ``too_broad`` means the query only named a make, so ``suggestions`` lists
    the models in stock instead of every variant. ``truncated`` means more
    listings matched than ``matches`` contains.
    """

    query: str
    matches: list[CarOffer]
    total: int
    truncated: bool
    too_broad: bool
    suggestions: list[str]


def format_price(price: int) -> str:
    """Format a catalog price as Pakistani rupees."""
    return f"PKR {price:,}"


def _norm(text: str) -> str:
    text = text.lower().replace("-", " ")
    text = re.sub(r"[^a-z0-9.\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _phrase_in(query: str, phrase: str) -> bool:
    return f" {phrase} " in f" {query} "


def _require_columns(
    path: Path, fieldnames: list[str] | None, required: tuple[str, ...]
) -> None:
    missing = [name for name in required if not fieldnames or name not in fieldnames]
    if missing:
        raise CatalogError(f"{path.name} is missing columns: {', '.join(missing)}")


def _load_dealers(path: Path) -> dict[int, Dealer]:
    if not path.is_file():
        raise CatalogError(f"Dealer file not found: {path}")

    dealers: dict[int, Dealer] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        _require_columns(path, reader.fieldnames, DEALER_COLUMNS)
        for line_no, row in enumerate(reader, start=2):
            try:
                dealer_id = int(row["id"])
                dealer = Dealer(
                    id=dealer_id,
                    name=row["name"].strip(),
                    phone=row["phone"].strip(),
                    email=row["email"].strip(),
                    city=row["city"].strip(),
                    address=row["address"].strip(),
                )
            except (TypeError, ValueError) as exc:
                raise CatalogError(
                    f"Invalid dealer row {line_no} in {path.name}"
                ) from exc
            if not dealer.name:
                raise CatalogError(f"Dealer row {line_no} in {path.name} has no name")
            if dealer_id in dealers:
                logger.warning(
                    "Duplicate dealer id %s in %s; keeping the first",
                    dealer_id,
                    path.name,
                )
                continue
            dealers[dealer_id] = dealer

    if not dealers:
        raise CatalogError(f"Dealer file is empty: {path}")
    return dealers


def _load_cars(path: Path, dealers: dict[int, Dealer]) -> list[Car]:
    if not path.is_file():
        raise CatalogError(f"Car file not found: {path}")

    cars: list[Car] = []
    seen: set[int] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        _require_columns(path, reader.fieldnames, CAR_COLUMNS)
        for line_no, row in enumerate(reader, start=2):
            try:
                car_id = int(row["id"])
                car = Car(
                    id=car_id,
                    make=row["make"].strip(),
                    model=row["model"].strip(),
                    variant=row["variant"].strip(),
                    price=int(row["price"]),
                    dealer_id=int(row["dealer_id"]),
                )
            except (TypeError, ValueError) as exc:
                raise CatalogError(f"Invalid car row {line_no} in {path.name}") from exc
            if not car.make or not car.model:
                raise CatalogError(
                    f"Car row {line_no} in {path.name} has no make or model"
                )
            if car_id in seen:
                logger.warning(
                    "Duplicate car id %s in %s; keeping the first", car_id, path.name
                )
                continue
            seen.add(car_id)
            if car.dealer_id not in dealers:
                logger.warning(
                    "Car %s references missing dealer id %s", car_id, car.dealer_id
                )
            cars.append(car)

    if not cars:
        raise CatalogError(f"Car file is empty: {path}")
    return cars


class Catalog:
    """In-memory car and dealer catalog loaded from CSV files."""

    def __init__(self, cars: list[Car], dealers: dict[int, Dealer]):
        self.cars = cars
        self.dealers = dealers
        self._makes = sorted({car.make for car in cars})
        self._models = sorted({car.model for car in cars}, key=len, reverse=True)

    @classmethod
    def from_csv(cls, cars_path: Path, dealers_path: Path) -> "Catalog":
        """Load both CSV files. Raises ``CatalogError`` when they cannot be used."""
        dealers = _load_dealers(dealers_path)
        cars = _load_cars(cars_path, dealers)
        logger.info("Loaded %s cars and %s dealers", len(cars), len(dealers))
        return cls(cars, dealers)

    def offer_for(self, car: Car) -> CarOffer:
        return CarOffer(car=car, dealer=self.dealers.get(car.dealer_id))

    def inventory_summary(self) -> str:
        """Compact make-and-model list for the system prompt."""
        grouped: dict[str, set[str]] = {}
        for car in self.cars:
            grouped.setdefault(car.make, set()).add(car.model)
        lines = [
            f"- {make}: {', '.join(sorted(models))}"
            for make, models in sorted(grouped.items())
        ]
        return "Cars in stock (make: models):\n" + "\n".join(lines)

    def search(self, query: str | None) -> SearchResult:
        """Find cars for a shopper phrase.

        Matching is deterministic: make, then model, then variant tokens, then
        dealer name and city. Nothing is invented when the query misses.
        """
        normalized = _norm(query or "")
        if not normalized:
            return SearchResult(
                query="",
                matches=[],
                total=0,
                truncated=False,
                too_broad=False,
                suggestions=[],
            )

        matched_models = self._models_in_query(normalized)
        matched_makes = [
            make for make in self._makes if _phrase_in(normalized, _norm(make))
        ]

        if matched_models:
            offers = [
                self.offer_for(car)
                for car in self.cars
                if car.model in matched_models
                and (not matched_makes or car.make in matched_makes)
            ]
            offers = self._narrow(offers, normalized)
            return self._pack(normalized, offers, too_broad=False, suggestions=[])

        if matched_makes:
            suggestions = sorted(
                {
                    f"{car.make} {car.model}"
                    for car in self.cars
                    if car.make in matched_makes
                }
            )
            return SearchResult(
                query=normalized,
                matches=[],
                total=0,
                truncated=False,
                too_broad=True,
                suggestions=suggestions,
            )

        return SearchResult(
            query=normalized,
            matches=[],
            total=0,
            truncated=False,
            too_broad=False,
            suggestions=[],
        )

    def _models_in_query(self, query: str) -> list[str]:
        found = [model for model in self._models if _phrase_in(query, _norm(model))]
        kept: list[str] = []
        for model in found:
            norm_model = _norm(model)
            if any(_norm(longer).startswith(norm_model + " ") for longer in kept):
                continue
            kept.append(model)
        return kept

    def _narrow(self, offers: list[CarOffer], query: str) -> list[CarOffer]:
        if not offers:
            return []

        scored = [(self._variant_score(offer.car, query), offer) for offer in offers]
        best = max(score for score, _ in scored)
        if best > 0:
            offers = [offer for score, offer in scored if score == best]

        dealer_hits = [
            offer
            for offer in offers
            if offer.dealer and _phrase_in(query, _norm(offer.dealer.name))
        ]
        if dealer_hits:
            offers = dealer_hits

        city_hits = [
            offer
            for offer in offers
            if offer.dealer and _phrase_in(query, _norm(offer.dealer.city))
        ]
        if city_hits:
            offers = city_hits

        offers.sort(
            key=lambda offer: (
                offer.car.make,
                offer.car.model,
                offer.car.variant,
                offer.dealer.name if offer.dealer else "",
            )
        )
        return offers

    def _variant_score(self, car: Car, query: str) -> int:
        tokens = [token for token in _norm(car.variant).split() if token]
        if not tokens:
            return 0
        return sum(1 for token in tokens if _phrase_in(query, token))

    def _pack(
        self,
        query: str,
        offers: list[CarOffer],
        *,
        too_broad: bool,
        suggestions: list[str],
    ) -> SearchResult:
        total = len(offers)
        truncated = total > LISTING_LIMIT
        return SearchResult(
            query=query,
            matches=offers[:LISTING_LIMIT],
            total=total,
            truncated=truncated,
            too_broad=too_broad,
            suggestions=suggestions,
        )


_catalog: Catalog | None = None


def get_catalog() -> Catalog:
    """Return the process-wide catalog, loading it from configured CSV paths."""
    global _catalog
    if _catalog is None:
        from app.configs import settings

        _catalog = Catalog.from_csv(settings.CARS_CSV, settings.DEALERS_CSV)
    return _catalog


def format_offers(
    result: SearchResult,
    *,
    include_phone: bool = False,
    include_address: bool = False,
) -> str:
    """Render search hits as plain text the model is allowed to quote."""
    if not result.query:
        return "No car has been identified yet."
    if result.too_broad:
        listed = ", ".join(result.suggestions) if result.suggestions else "none"
        return (
            "The request only named a make, so no single car was selected. "
            f"Models in stock: {listed}."
        )
    if not result.matches:
        return f"No car in the catalog matched {result.query!r}."

    lines: list[str] = []
    if result.truncated:
        lines.append(
            f"Showing {len(result.matches)} of {result.total} matches. "
            "Ask the customer to narrow by variant, dealer, or city."
        )
    for index, offer in enumerate(result.matches, start=1):
        car = offer.car
        if offer.dealer is None:
            dealer_text = (
                f"dealer record missing for id {car.dealer_id}. "
                "Do not invent contact details."
            )
        else:
            dealer_text = f"sold by {offer.dealer.name} in {offer.dealer.city}"
            if include_phone:
                dealer_text += f", phone {offer.dealer.phone}"
            if include_address:
                dealer_text += (
                    f", email {offer.dealer.email}, address {offer.dealer.address}"
                )
        lines.append(
            f"{index}. {car.make} {car.model} {car.variant} — {format_price(car.price)} — {dealer_text}"
        )
    return "\n".join(lines)
