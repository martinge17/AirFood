# AirFood

Serves the live Aramark menu over **plain HTTP only** — no browser — plus a lean PWA at the domain root:

- `/` — PWA menu web app (Vite + Svelte island in `web/`, built into the image)
- `/api/stores`, `/api/menu?...` — JSON API (FastAPI)
- `/health`
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
- `GET /api/stores` — the 10 menu stores
- `GET /api/menu?store=Airbus%20Finkenwerder&week=45&day=Tuesday` — week and day optional

## Web app

`web/` is a Vite + Svelte single-screen PWA: a month calendar (days with menu data are selectable, the rest grayed out) and receipt-style dish cards. `npm run build` in `web/` produces `dist/`, which the Dockerfile copies into the image and `main.py` mounts at `/`. No separate hosting needed.

**GitHub Pages variant:** Pages is static-only, so the API must run elsewhere. The workflow in `.github/workflows/pages.yml` builds `web/` on every push to `main` and deploys it to Pages at `https://<user>.github.io/AirFood/`. Set the repo secret `AIRFOOD_API_URL` to the deployed API's origin (e.g. `https://airfood.example.com`); the app then calls `<that>/api/*` cross-origin (the API sends permissive CORS by default, override with `CORS_ORIGINS`). Same-origin builds (the container) use relative `/api/*` and need no secret.

Checks: `uv run pytest`. Bruno collection in `bruno/` (`cd bruno && npx @usebruno/cli run -r --env local`).
