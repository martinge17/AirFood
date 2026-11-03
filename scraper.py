import os
import re
from urllib.parse import quote, urljoin

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

PORTAL = "https://aramark.cateringportal.io/menu"
PORTAL_ORIGIN = "https://aramark.cateringportal.io"

STORES = {
    store["name"]: {
        **store,
        "path": f"{quote(store['name'], safe='')}/{quote(store['menu'], safe='')}",
    }
    for store in (
        {"name": "Airbus Finkenwerder", "menu": "Casino HH-Finkenwerder"},
        {
            "name": "Betriebsrestaurant Fuhlsbüttel",
            "menu": "Betriebsrestaurant HH-Fuhlsbüttel",
        },
        {"name": "Bistro Halle 9", "menu": "Bistro Halle 9"},
        {"name": "Casino", "menu": "Casino HH-Finkenwerder"},
        {"name": "Elbblick", "menu": "Elbblick HH-Finkenwerder"},
        {"name": "Kantine Hs. 18", "menu": "Kantine Hs. 18, HH-Finkenwerder"},
        {"name": "Marché", "menu": "Marché HH-Finkenwerder"},
        {"name": "Sharklet Hs. 100", "menu": "Sharklet Hs.100, Daily Menu"},
        {"name": "TUHH", "menu": "Airbus TU"},
        {"name": "ZAL TechCenter", "menu": "ZAL TechCenter"},
    )
}

DAY_NAMES = {
    "mon": "Monday",
    "monday": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "tuesday": "Tuesday",
    "wed": "Wednesday",
    "wednesday": "Wednesday",
    "thu": "Thursday",
    "thur": "Thursday",
    "thurs": "Thursday",
    "thursday": "Thursday",
    "fri": "Friday",
    "friday": "Friday",
    "sat": "Saturday",
    "saturday": "Saturday",
    "sun": "Sunday",
    "sunday": "Sunday",
}


class ScrapeError(Exception):
    pass


def normalize_day(day: str) -> str:
    normalized = DAY_NAMES.get(day.strip().lower())
    if not normalized:
        raise ValueError("day must be a weekday name, e.g. Tuesday")
    return normalized


def _day_name(label: str) -> str | None:
    match = re.match(r"([A-Za-z]+)", label.strip())
    return DAY_NAMES.get(match.group(1).lower()) if match else None


def _image_url(card) -> str | None:
    image = card.locator(".product-image")
    background = image.get_attribute("style") if image.count() else None
    match = re.search(r'url\(["\']?(.*?)["\']?\)', background or "")
    return urljoin(PORTAL_ORIGIN, match.group(1)) if match else None


def _prices(texts: list[str]) -> list[dict]:
    result = []
    for text in texts:
        match = re.search(r"^(.*?)\s*([€$£])\s*([\d.,]+)$", text.strip())
        if match:
            result.append(
                {
                    "label": match.group(1).strip() or None,
                    "amount": match.group(3),
                    "currency": {"€": "EUR", "$": "USD", "£": "GBP"}[match.group(2)],
                }
            )
    return result


def _meal(card, category: str) -> dict:
    prices = _prices(card.locator(".price").all_inner_texts())
    label_list = card.locator(".label-list:not(.customtag-list) span")
    return {
        "name": card.locator(".product-title button").inner_text().strip(),
        "category": category,
        "price": prices[0]["amount"] if prices else None,
        "currency": prices[0]["currency"] if prices else None,
        "price_options": prices,
        "allergens": [value.strip() for value in label_list.all_inner_texts()],
        "tags": [
            {"name": image.get_attribute("alt"), "image_url": image.get_attribute("src")}
            for image in card.locator("app-product-custom-tag img").all()
        ],
        "image_url": _image_url(card),
    }


def _js_click(page, selector: str, text: str | None = None) -> bool:
    return page.evaluate(
        r"""([selector, text]) => {
            const norm = s => s.innerText.replace(/\s+/g, ' ').trim();
            const el = [...document.querySelectorAll(selector)]
                .find(e => !text || norm(e) === text || e.innerText.split(/\n/)[0].trim() === text);
            if (!el) return false;
            el.click();
            return true;
        }""",
        [selector, text],
    )


def _week_options(page) -> list[str]:
    page.wait_for_timeout(300)
    return [t for t in (
        " ".join(x.split()) for x in page.evaluate(
            "() => [...document.querySelectorAll('.mat-mdc-option')].map(o => o.innerText)")
    ) if t]


def _select_week(page, week: int) -> None:
    # JS-driven select; Playwright's geometric clicks fail on engines without full layout (Obscura).
    page.evaluate("() => document.querySelector('.mat-mdc-select')?.click()")
    page.wait_for_timeout(500)
    if _js_click(page, ".mat-mdc-option", f"CW: {week}"):
        page.wait_for_timeout(1000)  # tabs re-render async on week switch
        return
    available = _week_options(page)
    raise ValueError(f"week {week} is not available; portal offers {', '.join(available)}")


def _open_day(page, label: str) -> None:
    _js_click(page, '[role="tab"]', label)
    page.wait_for_timeout(400)


def _read_day(page, tab, tab_label: str) -> dict:
    # class-based state: aria-selected is unreliable across engines (missing on Obscura)
    if "mdc-tab--active" not in (tab.get_attribute("class") or ""):
        _open_day(page, tab_label)
        page.wait_for_timeout(500)

    meals = []
    for category in page.locator("app-category").all():
        heading = category.locator("h3").inner_text().strip()
        meals.extend(_meal(card, heading) for card in category.locator("mat-card.product-card").all())
    return {"label": tab_label, "weekday": _day_name(tab_label), "meals": meals}


def _browser(playwright):
    # BROWSER_WS targets a remote Chromium (compose `browser` service); unset scrapes with a locally launched one.
    ws = os.environ.get("BROWSER_WS")
    if ws:
        token = os.environ.get("BROWSER_WS_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else None
        browser = playwright.chromium.connect_over_cdp(ws, headers=headers)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
    else:
        browser = playwright.chromium.launch(args=["--no-sandbox"])
        context = browser.new_context(locale="en-US")
    return browser, context


def fetch_menu(store: dict, week: int | None = None, day: str | None = None) -> dict:
    url = f"{PORTAL}/{store['path']}"
    try:
        with sync_playwright() as playwright:
            browser, context = _browser(playwright)
            try:
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                # portal shows "No data found" instead of cards for empty stores
                page.locator("mat-card.product-card").or_(
                    page.get_by_text("No data found")
                ).first.wait_for(timeout=45000)
                if not page.locator("mat-card.product-card").count():
                    return {
                        "store": store["name"],
                        "menu": store["menu"],
                        "week": None,
                        "days": [],
                    }
                week_selector = page.get_by_role("combobox", name=re.compile(r"^CW:"))
                selected_week = week_selector.inner_text().strip()
                if week is not None and int(re.search(r"\d+", selected_week).group()) != week:
                    _select_week(page, week)
                    selected_week = week_selector.inner_text().strip()

                days = []
                for tab in page.get_by_role("tab").all():
                    label = " ".join(tab.inner_text().split())
                    weekday = _day_name(label)
                    if not weekday or "mat-mdc-tab-disabled" in (tab.get_attribute("class") or "") or (day and weekday != day):
                        continue
                    days.append(_read_day(page, tab, label))

                if day and not days:
                    raise ValueError(f"{day} is not available in {selected_week}")
                return {
                    "store": store["name"],
                    "menu": store["menu"],
                    "week": selected_week,
                    "days": days,
                }
            finally:
                browser.close()
    except ValueError:
        raise
    except (PlaywrightTimeoutError, PlaywrightError) as error:
        raise ScrapeError(f"Could not read menu from the Aramark portal: {error}") from error
