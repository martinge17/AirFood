import pytest

from scraper import STORES, _prices, normalize_day


def test_store_directory_matches_menu_options():
    assert len(STORES) == 10
    assert STORES["Airbus Finkenwerder"]["menu"] == "Casino HH-Finkenwerder"
    assert STORES["Marché"]["path"] == "March%C3%A9/March%C3%A9%20HH-Finkenwerder"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("Tue", "Tuesday"), ("wednesday", "Wednesday"), ("FRI", "Friday")],
)
def test_normalize_day(value, expected):
    assert normalize_day(value) == expected


def test_normalize_day_rejects_invalid_value():
    with pytest.raises(ValueError):
        normalize_day("Someday")


def test_prices_preserve_multiple_price_labels():
    assert _prices(["€9.25", "intern  €7.25"]) == [
        {"label": None, "amount": "9.25", "currency": "EUR"},
        {"label": "intern", "amount": "7.25", "currency": "EUR"},
    ]
