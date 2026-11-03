"""HTTP-only menu backend.

Replaces the browser path with the request chain reverse-engineered from the
Aramark catering portal (Qnips backend):

1. GET  apps-live-eu.qnips.com/cons/api/FirebaseInfo   -> CustomToken
2. POST identitytoolkit.../accounts:signInWithCustomToken -> idToken (1 h)
3. GET  firestore.googleapis.com/v1/.../documents/...  -> stores and menus

Firestore paths (verified against the live SPA):
- Release/en-US/StoreMetas                              -> stores + menu ids
- Release/en-US/Menus/{menuId}/Years/{year}/Weeks/{cw}  -> week doc, days inline
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from scraper import ScrapeError, _day_name

QNIPS_BASE = "https://apps-live-eu.qnips.com/cons/api"
FIRESTORE_BASE = (
    "https://firestore.googleapis.com/v1"
    "/projects/q-aramark/databases/(default)/documents"
)
FIREBASE_API_KEY = "AIzaSyBC7KHOACAPWb0DwSceR3ZdoO-BUMfgoSw"
# "0" + apiKey per the portal bundle; verified working against FirebaseInfo.
QNIPS_AUTH_HEADER = os.environ.get("QNIPS_AUTH_HEADER", "007774ebf508aa88e44eab2baf833ae97c")
QNIPS_BRAND = os.environ.get("QNIPS_BRAND", "aramark")
LANGUAGE = "en-US"

_token = {"value": None, "expires": 0}
_menu_ids = {"value": None, "expires": 0}


def _request(url: str, headers: dict, data: bytes | None = None) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def _id_token() -> str:
    """Custom-token sign-in, cached; re-signs 5 minutes before expiry."""
    if _token["value"] and time.monotonic() < _token["expires"]:
        return _token["value"]
    _, body = _request(
        f"{QNIPS_BASE}/FirebaseInfo",
        {
            "Authorization": QNIPS_AUTH_HEADER,
            "App-Brand": QNIPS_BRAND,
            "Response-Version": "v3",
        },
    )
    custom_token = json.loads(body).get("CustomToken")
    if not custom_token:
        raise ScrapeError("FirebaseInfo did not return a CustomToken")
    status, body = _request(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken"
        f"?key={FIREBASE_API_KEY}",
        {"Content-Type": "application/json"},
        json.dumps({"token": custom_token, "returnSecureToken": True}).encode(),
    )
    if status != 200:
        raise ScrapeError(f"Firebase sign-in failed: {body.decode(errors='ignore')[:200]}")
    result = json.loads(body)
    _token["value"] = result["idToken"]
    _token["expires"] = time.monotonic() + int(result.get("expiresIn", 3600)) - 300
    return _token["value"]


def _firestore_get(path: str) -> bytes | None:
    """GET a Firestore REST document/collection; None on 404; re-signs once on 401."""
    for attempt in (1, 2):
        status, body = _request(
            f"{FIRESTORE_BASE}/{path}",
            {"Authorization": f"Bearer {_id_token()}"},
        )
        if status == 200:
            return body
        if status == 404:
            return None
        if status == 401 and attempt == 1:
            _token["expires"] = 0  # force re-sign
            continue
        raise ScrapeError(f"Firestore read failed ({status}): {body.decode(errors='ignore')[:200]}")
    return None


def _menu_id(menu_name: str) -> str:
    if _menu_ids["value"] is None or time.monotonic() > _menu_ids["expires"]:
        body = _firestore_get(f"Release/{LANGUAGE}/StoreMetas?pageSize=100")
        if body is None:
            raise ScrapeError("StoreMetas collection not found")
        index = {}
        for document in json.loads(body).get("documents", []):
            for store in document["fields"].get("Stores", {}).get("arrayValue", {}).get("values", []):
                for menu in store["mapValue"]["fields"].get("Menus", {}).get("arrayValue", {}).get("values", []):
                    fields = menu["mapValue"]["fields"]
                    name = fields.get("Name", {}).get("stringValue")
                    menu_id = (fields.get("Id") or {}).get("integerValue")
                    if name and menu_id and fields.get("ShowInCateringPortal", {}).get("booleanValue"):
                        index[name] = menu_id
        if not index:
            raise ScrapeError("StoreMetas contained no catering-portal menus")
        _menu_ids["value"] = index
        _menu_ids["expires"] = time.monotonic() + 3600
    if menu_name not in _menu_ids["value"]:
        raise ScrapeError(f"Menu not known to the portal: {menu_name}")
    return _menu_ids["value"][menu_name]


def _week_path(menu_id: str, week: int | None) -> tuple[str, int]:
    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    if week is None:
        return f"{iso_year}", iso_week
    # ISO-year boundary: week 1 requested late in the year belongs to the next
    # ISO year, and week 52/53 requested in early January to the previous one.
    year = iso_year + (1 if week == 1 and iso_week >= 52 else -1 if week >= 52 and iso_week == 1 else 0)
    return f"{year}", week


def _label_list(product: dict, week_fields: dict, key: str) -> list[str]:
    """Map product id references to labels via the week-level lookup tables."""
    ids = [v["integerValue"] for v in product.get(key, {}).get("arrayValue", {}).get("values", [])]
    if not ids:
        return []
    entries = week_fields.get(key, {}).get("arrayValue", {}).get("values", [])
    by_id = {}
    for entry in entries:
        fields = entry.get("mapValue", {}).get("fields", {})
        entry_id = (fields.get("AllergenId") or fields.get("Id") or {}).get("integerValue")
        label = fields.get("Label", {}).get("stringValue")
        if entry_id is not None and label:
            by_id.setdefault(entry_id, label)
    # main allergen letters only ("A1" -> "A"); additive labels are plain digits
    return [
        re.sub(r"\d+$", "", by_id[i]) if by_id[i][:1].isalpha() else by_id[i]
        for i in ids
        if i in by_id
    ]


def _prices(product: dict) -> list[dict]:
    result = []
    prices = product.get("Prices", {}).get("arrayValue", {}).get("values", [])
    for price in prices:
        fields = price.get("mapValue", {}).get("fields", {})
        amount = fields.get("Price", {}).get("doubleValue")
        currency = (
            fields.get("LocalizablePrice", {}).get("mapValue", {}).get("fields", {}).get("CurrencyCode", {}).get("stringValue")
        )
        if amount is None:
            continue
        result.append(
            {
                "label": fields.get("Label", {}).get("stringValue"),
                "amount": f"{amount:.2f}",
                "currency": currency,
            }
        )
    return result


def _meal(product: dict, category: str, week_fields: dict) -> dict:
    prices = _prices(product)
    tags = product.get("CustomTags", {}).get("arrayValue", {}).get("values", [])
    return {
        "name": product.get("Name", {}).get("stringValue"),
        "category": category,
        "price": prices[0]["amount"] if prices else None,
        "currency": prices[0]["currency"] if prices else None,
        "price_options": prices,
        "allergens": _label_list(product, week_fields, "Allergens")
        + _label_list(product, week_fields, "Additives"),
        "tags": [
            {
                "name": tag["mapValue"]["fields"].get("Name", {}).get("stringValue"),
                "image_url": tag["mapValue"]["fields"].get("IconUrl", {}).get("stringValue"),
            }
            for tag in tags
        ],
        "image_url": product.get("PictureUrl", {}).get("stringValue"),
    }


def _week_days(week_fields: dict) -> list[dict]:
    # the portal disables past days; mirror that using the week's own timezone
    zone = ZoneInfo(week_fields.get("TimeZoneId", {}).get("stringValue", "UTC"))
    today = datetime.now(zone).date()
    days = []
    for day in week_fields.get("Days", {}).get("arrayValue", {}).get("values", []):
        fields = day.get("mapValue", {}).get("fields", {})
        day_date = datetime.fromisoformat(
            fields.get("Date", {}).get("timestampValue", "").replace("Z", "+00:00")
        ).astimezone(zone)
        if day_date.date() < today:
            continue
        label = day_date.strftime("%a. %d.%m.")
        meals = []
        for category in fields.get("Categories", {}).get("arrayValue", {}).get("values", []):
            category_fields = category["mapValue"]["fields"]
            if category_fields.get("IsHidden", {}).get("booleanValue"):
                continue
            name = category_fields.get("Name", {}).get("stringValue")
            for product in category_fields.get("Products", {}).get("arrayValue", {}).get("values", []):
                meals.append(_meal(product["mapValue"]["fields"], name, week_fields))
        days.append({"label": label, "weekday": _day_name(label), "meals": meals})
    return days


def fetch_menu(store: dict, week: int | None = None, day: str | None = None) -> dict:
    menu_id = _menu_id(store["menu"])
    year, week_number = _week_path(menu_id, week)
    body = _firestore_get(f"Release/{LANGUAGE}/Menus/{menu_id}/Years/{year}/Weeks/{week_number}")
    if body is None:
        raise ValueError(f"week {week_number} is not available in the portal")
    week_fields = json.loads(body)["fields"]
    days = _week_days(week_fields)
    if day:
        days = [entry for entry in days if entry["weekday"] == day]
        if not days:
            raise ValueError(f"{day} is not available in CW: {week_number}")
    return {
        "store": store["name"],
        "menu": store["menu"],
        "week": f"CW: {week_number}",
        "days": days,
    }
