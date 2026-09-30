from pathlib import Path

import pytest

from app.services.catalog import Catalog, CatalogError, format_offers, format_price

ROOT = Path(__file__).resolve().parents[1]
CARS = ROOT / "inputs" / "cars.csv"
DEALERS = ROOT / "inputs" / "dealers.csv"


@pytest.fixture
def catalog() -> Catalog:
    return Catalog.from_csv(CARS, DEALERS)


def test_corolla_does_not_include_corolla_cross(catalog: Catalog) -> None:
    result = catalog.search("Toyota Corolla")
    assert result.matches
    assert all(offer.car.model == "Corolla" for offer in result.matches)
    assert result.truncated or result.total > 1


def test_corolla_cross_does_not_include_corolla(catalog: Catalog) -> None:
    result = catalog.search("Toyota Corolla Cross")
    assert result.matches
    assert {offer.car.model for offer in result.matches} == {"Corolla Cross"}


def test_variant_and_dealer_narrow_to_one_listing(catalog: Catalog) -> None:
    result = catalog.search("Toyota Corolla Altis Grande 1.8 Crown Toyota")
    assert result.total == 1
    offer = result.matches[0]
    assert offer.car.variant == "Altis Grande 1.8"
    assert offer.dealer is not None
    assert offer.dealer.name == "Crown Toyota"
    assert offer.dealer.phone == "0300-4112201"
    assert offer.dealer.city == "Karachi"


def test_unknown_car_returns_no_matches(catalog: Catalog) -> None:
    result = catalog.search("BMW X5")
    assert result.matches == []
    assert result.too_broad is False


def test_make_only_is_too_broad(catalog: Catalog) -> None:
    result = catalog.search("Toyota")
    assert result.too_broad is True
    assert result.matches == []
    assert "Toyota Corolla" in result.suggestions
    assert "Toyota Corolla Cross" in result.suggestions


def test_empty_query_matches_nothing(catalog: Catalog) -> None:
    result = catalog.search("   ")
    assert result.total == 0
    assert result.query == ""


def test_format_price_uses_pkr() -> None:
    assert format_price(9250000) == "PKR 9,250,000"


def test_contact_details_stay_hidden_until_requested(catalog: Catalog) -> None:
    result = catalog.search("Toyota Corolla Altis Grande 1.8 Crown Toyota")
    hidden = format_offers(result)
    shown = format_offers(result, include_phone=True, include_address=True)
    assert "0300-4112201" not in hidden
    assert "0300-4112201" in shown
    assert "sales@crowntoyota.example" in shown


def test_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "dealers.csv"
    with pytest.raises(CatalogError, match="not found"):
        Catalog.from_csv(tmp_path / "cars.csv", missing)


def test_missing_dealer_is_reported_without_inventing_contact(tmp_path: Path) -> None:
    dealers = tmp_path / "dealers.csv"
    cars = tmp_path / "cars.csv"
    dealers.write_text(
        "id,name,phone,email,city,address\n1,Only Dealer,0300,a@b.c,Karachi,1 Road\n",
        encoding="utf-8",
    )
    cars.write_text(
        "id,make,model,variant,price,dealer_id\n1,Toyota,Corolla,GLi,100,99\n",
        encoding="utf-8",
    )
    catalog = Catalog.from_csv(cars, dealers)
    result = catalog.search("Toyota Corolla")
    assert result.total == 1
    assert result.matches[0].dealer is None
    text = format_offers(result, include_phone=True)
    assert "dealer record missing" in text
    assert "0300" not in text


def test_bad_columns_raise(tmp_path: Path) -> None:
    dealers = tmp_path / "dealers.csv"
    cars = tmp_path / "cars.csv"
    dealers.write_text("id,name\n1,Nobody\n", encoding="utf-8")
    cars.write_text("id,make\n1,Toyota\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="missing columns"):
        Catalog.from_csv(cars, dealers)
