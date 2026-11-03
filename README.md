# AirFood

FastAPI service that reads the live Aramark menu. Two interchangeable backends:

- `backend=browser` (default): renders the portal in a remote headless browser (Obscura via CDP, see `compose.yaml`)
- `backend=http`: plain HTTP only, using the reverse-engineered Qnips/Firebase request chain (`qmenu_http.py`) — no browser needed

Menu options and the reverse-engineered source behavior are documented in [`original_api.md`](original_api.md).

## Run with Docker Compose (API + browser service)

```sh
docker compose up -d --build
```

API on <http://localhost:8000/docs>. Both services use the host network because Obscura v0.2.6 binds CDP to loopback inside its netns. Set `BROWSER_WS_TOKEN` to change the shared CDP token (default is a dev token).

## Run standalone (local Chromium)

```sh
docker build -t airfood .
docker run --rm -p 8000:8000 -e AIRFOOD_BACKEND=http airfood   # HTTP backend, no browser at all
docker run --rm -p 8000:8000 airfood                            # browser backend, needs local Chromium
```

## Run locally

```sh
uv sync
uv run playwright install chromium   # only for backend=browser
uv run uvicorn main:app --reload
```

## API

- `GET /api/stores` — menu-enabled stores
- `GET /api/menu?store=Airbus%20Finkenwerder&week=45` — all enabled days in an available portal week
- Add `&day=Tuesday` to filter to one weekday, `&backend=http` to use the HTTP-only path
- `GET /health` — health check

The portal only offers a rolling set of weeks and disables past days. Scraped ingredient-like text remains part of the dish name because the portal does not expose it as a structured ingredient list.

## Bruno

With the API running, execute the requests in the collection:

```sh
cd bruno
npx @usebruno/cli run -r --env local
```

Run checks with `uv run pytest`.
