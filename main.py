import os

from fastapi import FastAPI, HTTPException, Query

from scraper import ScrapeError, STORES, fetch_menu, normalize_day
import qmenu_http

app = FastAPI(title="AirFood", description="Aramark menu data", version="0.2.0")

# "browser" = render the portal in Chromium/Obscura; "http" = plain HTTP with the
# reverse-engineered Qnips/Firebase token chain (qmenu_http). Override per request
# with ?backend= or globally with AIRFOOD_BACKEND.
DEFAULT_BACKEND = os.environ.get("AIRFOOD_BACKEND", "browser")
BACKENDS = {"browser": fetch_menu, "http": qmenu_http.fetch_menu}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/stores")
def stores():
    return list(STORES.values())


@app.get("/api/menu")
def menu(
    store: str = Query("Airbus Finkenwerder"),
    week: int | None = Query(None, ge=1, le=53),
    day: str | None = Query(None),
    backend: str = Query(DEFAULT_BACKEND),
):
    if backend not in BACKENDS:
        raise HTTPException(422, detail=f"backend must be one of: {', '.join(BACKENDS)}")
    if store not in STORES:
        raise HTTPException(404, detail=f"Unknown menu store: {store}")
    try:
        day_filter = normalize_day(day) if day else None
        return BACKENDS[backend](STORES[store], week=week, day=day_filter)
    except ValueError as error:
        raise HTTPException(422, detail=str(error)) from error
    except ScrapeError as error:
        raise HTTPException(502, detail=str(error)) from error
