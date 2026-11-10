import calendar
import json
from datetime import datetime, timedelta, timezone

import pytest

import qmenu_http


def today():
    return datetime.now(timezone.utc).date()


def fs_str(value):
    return {"stringValue": value}


def fs_int(value):
    return {"integerValue": str(value)}


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
    class FakeDateTime:
        @staticmethod
        def now(tz=None):
            return datetime(2026, 12, 28, tzinfo=timezone.utc)  # ISO week 53 of 2026

    monkeypatch.setattr(qmenu_http, "datetime", FakeDateTime)
    assert qmenu_http._week_path(1) == ("2027", 1)
    assert qmenu_http._week_path(45) == ("2026", 45)


def _iso(offset_days: int) -> str:
    return (today() + timedelta(days=offset_days)).isoformat() + "T00:00:00Z"


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
    today_date = today()
    assert day_result["label"] == f"{qmenu_http.EN_ABBR[today_date.isoweekday() - 1]}. {today_date.day:02d}.{today_date.month:02d}."
    assert day_result["weekday"] == calendar.day_name[today_date.weekday()]
    meal = day_result["meals"][0]
    assert meal["name"] == "Minestrone"
    assert meal["category"] == "Suppentopf"
    assert meal["price"] == "1.80"
    assert meal["currency"] == "EUR"
    assert meal["allergens"] == ["A"]
    assert meal["tags"] == [{"name": "Vegetarian", "image_url": "https://files.qnips.com/veg.png"}]
    assert meal["image_url"] == "https://files.qnips.com/Minestrone.png"
    assert meal["kcal"] is None  # fixture product has no NutritionFacts


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
    result = qmenu_http.fetch_menu(store, week=45, day=calendar.day_name[(today() + timedelta(days=1)).weekday()])
    assert len(result["days"]) == 1
    absent = calendar.day_name[(today() + timedelta(days=2)).weekday()]  # not today or tomorrow
    with pytest.raises(ValueError):
        qmenu_http.fetch_menu(store, week=45, day=absent)


def test_kcal_prefers_serving_then_per100():
    with_serving = {"NutritionFacts": fs_map({"KCalPer100": fs_int(100), "KCalPerServing": fs_int(400)})}
    assert qmenu_http._kcal(with_serving) == 400.0
    only_100 = {"NutritionFacts": fs_map({"KCalPer100": fs_int(100)})}
    assert qmenu_http._kcal(only_100) == 100.0
    assert qmenu_http._kcal({}) is None


def test_fetch_menu_unknown_week_is_client_error(monkeypatch):
    monkeypatch.setattr(qmenu_http, "_menu_id", lambda name: "12246")
    monkeypatch.setattr(qmenu_http, "_firestore_get", lambda path: None)
    with pytest.raises(ValueError):
        qmenu_http.fetch_menu({"name": "Casino", "menu": "Casino HH-Finkenwerder"}, week=2)


def test_fetch_product_returns_nutrition_and_allergen_details(monkeypatch):
    facts = fs_map(
        {
            "KCalPer100": fs_int(135),
            "FatsPer100": {"doubleValue": 3.6},
            "KCalPerServing": fs_int(554),
            "ProteinsPerServing": {"doubleValue": 20.7},
        }
    )
    prod = product("Crispy rice bowl", allergens=(0,), prices=(5.5,))
    prod["mapValue"]["fields"]["Id"] = fs_int(22956435)
    prod["mapValue"]["fields"]["NutritionFacts"] = facts
    prod["mapValue"]["fields"]["WeightInGrams"] = {"doubleValue": 450}
    doc = week_doc([day(_iso(0), [category("salad garden", [prod])])])
    monkeypatch.setattr(qmenu_http, "_menu_id", lambda name: "12253")
    monkeypatch.setattr(qmenu_http, "_firestore_get", lambda path: doc)

    result = qmenu_http.fetch_product({"name": "Kantine Hs. 18", "menu": "Kantine Hs. 18, HH-Finkenwerder"}, "22956435", week=45)
    assert result["id"] == "22956435"
    assert result["name"] == "Crispy rice bowl"
    assert result["nutrition"]["per_100g"] == {"Calories (kcal)": 135.0, "Fat (g)": 3.6}
    assert result["nutrition"]["per_serving"] == {"Calories (kcal)": 554.0, "Protein (g)": 20.7}
    assert result["weight_grams"] == 450
    assert result["allergen_details"] == [{"label": "A1", "name": None}] or result["allergen_details"][0]["label"] == "A1"
    with pytest.raises(ValueError):
        qmenu_http.fetch_product({"name": "Kantine Hs. 18", "menu": "Kantine Hs. 18, HH-Finkenwerder"}, "999", week=45)
