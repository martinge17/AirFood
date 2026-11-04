from fastapi import FastAPI, HTTPException, Query

from qmenu_http import STORES, ScrapeError, fetch_menu, normalize_day

app = FastAPI(title="AirFood", description="Aramark menu data via the reverse-engineered HTTP API", version="0.3.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stores")
def stores():
    return list(STORES.values())


@app.get("/menu")
def menu(
    store: str = Query("Airbus Finkenwerder"),
    week: int | None = Query(None, ge=1, le=53),
    day: str | None = Query(None),
):
    if store not in STORES:
        raise HTTPException(404, detail=f"Unknown menu store: {store}")
    try:
        day_filter = normalize_day(day) if day else None
        return fetch_menu(STORES[store], week=week, day=day_filter)
    except ValueError as error:
        raise HTTPException(422, detail=str(error)) from error
    except ScrapeError as error:
        raise HTTPException(502, detail=str(error)) from error
