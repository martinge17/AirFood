import json

import pytest

import qmenu_http
from scraper import ScrapeError


def fs_str(value):
    return {"stringValue": value}


def fs_int(value):
    return {"integerValue": str(value)}


def fs_bool(value):
    return {"booleanValue": value}


def fs_array(values):
    return {"arrayValue": {"values": values}}


def fs_map(fields):
    return {"mapValue": {"fields": fields}}


WEEK_FIELDS = {
    "Allergens": fs_array(
        [
            fs_map({"AllergenId": fs_int(0), "Label": fs_str("A1")}),
            fs_map({"AllergenId": fs_int(6), "Label": fs_str("G")}),
        ]
    ),
    "Additives": fs_array([fs_map({"Id": fs_int(1309), "Label": fs_str("3")})]),
}


def product(name, allergens=(), additives=(), prices=(1.8,), tags=()):
    return fs_map(
        {
            "Name": fs_str(name),
            "PictureUrl": fs_str(f"https://files.qnips.com/{name}.png"),
            "Allergens": fs_array([{"integerValue": str(a)} for a in allergens]),
            "Additives": fs_array([{"integerValue": str(a)} for a in additives]),
            "CustomTags": fs_array(
                [fs_map({"Name": fs_str(n), "IconUrl": fs_str(u)}) for n, u in tags]
            ),
            "Prices": fs_array(
                [
                    fs_map(
                        {
                            "Price": {"doubleValue": p},
                            "LocalizablePrice": fs_map({"CurrencyCode": fs_str("EUR")}),
                        }
                    )
                    for p in prices
                ]
            ),
        }
    )


def category(name, products):
    return fs_map({"Name": fs_str(name), "Products": fs_array(products)})


def day(date_iso, categories):
    return fs_map({"Date": {"timestampValue": date_iso}, "Categories": fs_array(categories)})


def week_doc(days):
    fields = dict(WEEK_FIELDS)
    fields["Days"] = fs_array(days)
    return json.dumps({"fields": fields}).encode()


def test_label_list_maps_ids_and_strips_sub_digits():
    product = {"Allergens": fs_array([{"integerValue": "0"}, {"integerValue": "6"}])}
    assert qmenu_http._label_list(product, WEEK_FIELDS, "Allergens") == ["A", "G"]


def test_label_list_maps_additive_ids():
    product = {"Additives": fs_array([{"integerValue": "1309"}])}
    assert qmenu_http._label_list(product, WEEK_FIELDS, "Additives") == ["3"]


def test_prices_preserve_labels_and_formatting():
    priced = {
        "Prices": fs_array(
                [
                    fs_map(
                        {
                            "Price": {"doubleValue": 9.25},
                            "LocalizablePrice": fs_map({"CurrencyCode": fs_str("EUR")}),
                        }
                    ),
                    fs_map(
                        {
                            "Price": {"doubleValue": 7.25},
                            "Label": fs_str("intern"),
                            "LocalizablePrice": fs_map({"CurrencyCode": fs_str("EUR")}),
                        }
                    ),
                ]
            )
    }
    assert qmenu_http._prices(priced) == [
        {"label": None, "amount": "9.25", "currency": "EUR"},
        {"label": "intern", "amount": "7.25", "currency": "EUR"},
    ]


def test_week_path_handles_iso_year_boundary(monkeypatch):
    class FakeDate(qmenu_http.date):
        @classmethod
        def today(cls):
            return cls(2026, 12, 28)  # ISO week 53 of 2026

    monkeypatch.setattr(qmenu_http, "date", FakeDate)
    assert qmenu_http._week_path("1", 1) == ("2027", 1)
    assert qmenu_http._week_path("1", 45) == ("2026", 45)


from datetime import timedelta


def _iso(offset_days: int) -> str:
    return (qmenu_http.date.today() + timedelta(days=offset_days)).isoformat() + "T00:00:00Z"


def test_fetch_menu_maps_week_doc(monkeypatch):
    doc = week_doc(
        [
            day(
                _iso(0),
                [
                    category(
                        "Suppentopf",
                        [
                            product(
                                "Minestrone",
                                allergens=(0,),
                                prices=(1.8,),
                                tags=(("Vegetarian", "https://files.qnips.com/veg.png"),),
                            )
                        ],
                    )
                ],
            )
        ]
    )
    monkeypatch.setattr(qmenu_http, "_menu_id", lambda name: "12246")
    monkeypatch.setattr(qmenu_http, "_firestore_get", lambda path: doc)

    result = qmenu_http.fetch_menu({"name": "Casino", "menu": "Casino HH-Finkenwerder"}, week=45)
    assert result["week"] == "CW: 45"
    day_result = result["days"][0]
    assert day_result["label"] == qmenu_http.date.today().strftime("%a. %d.%m.")
    assert day_result["weekday"] == qmenu_http.date.today().strftime("%A")
    meal = day_result["meals"][0]
    assert meal["name"] == "Minestrone"
    assert meal["category"] == "Suppentopf"
    assert meal["price"] == "1.80"
    assert meal["currency"] == "EUR"
    assert meal["allergens"] == ["A"]
    assert meal["tags"] == [{"name": "Vegetarian", "image_url": "https://files.qnips.com/veg.png"}]
    assert meal["image_url"] == "https://files.qnips.com/Minestrone.png"


def test_fetch_menu_day_filter(monkeypatch):
    doc = week_doc(
        [
            day(_iso(0), []),
            day(_iso(1), []),
        ]
    )
    monkeypatch.setattr(qmenu_http, "_menu_id", lambda name: "12246")
    monkeypatch.setattr(qmenu_http, "_firestore_get", lambda path: doc)
    store = {"name": "Casino", "menu": "Casino HH-Finkenwerder"}
    result = qmenu_http.fetch_menu(store, week=45, day=(qmenu_http.date.today() + timedelta(days=1)).strftime("%A"))
    assert len(result["days"]) == 1
    with pytest.raises(ValueError):
        qmenu_http.fetch_menu(store, week=45, day="Sunday")


def test_fetch_menu_unknown_week_is_client_error(monkeypatch):
    monkeypatch.setattr(qmenu_http, "_menu_id", lambda name: "12246")
    monkeypatch.setattr(qmenu_http, "_firestore_get", lambda path: None)
    with pytest.raises(ValueError):
        qmenu_http.fetch_menu({"name": "Casino", "menu": "Casino HH-Finkenwerder"}, week=2)


def test_scrape_error_is_shared_with_api():
    assert qmenu_http.ScrapeError is ScrapeError
