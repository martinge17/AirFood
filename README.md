# AirFood

FastAPI service that serves the live Aramark menu over **plain HTTP only** — no browser.
It uses the reverse-engineered request chain of the catering portal (Qnips `FirebaseInfo`
→ Firebase custom-token sign-in → Firestore REST v1), implemented in `qmenu_http.py`.
Details of the reverse engineering: [`original_api.md`](original_api.md).

The older browser-based variant (Playwright/Obscura scraping the SPA) lives in the
nested repo [`browser-api/`](browser-api/).

An agent skill for querying this API ("what's on the menu", recommendations) is in
[`skills/airfood/SKILL.md`](skills/airfood/SKILL.md).

## Run

```sh
docker compose up -d --build     # distroless Chainguard image, API on :8000
# or: docker build -t airfood . && docker run --rm -p 8000:8000 airfood
```

Local: `uv sync && uv run uvicorn main:app --reload`. Docs at <http://localhost:8000/docs>.

## API

- `GET /health`
- `GET /stores` — the 10 menu stores
- `GET /menu?store=Airbus%20Finkenwerder&week=45&day=Tuesday` — week and day optional

Checks: `uv run pytest`. Bruno collection in `bruno/` (`cd bruno && npx @usebruno/cli run -r --env local`).
