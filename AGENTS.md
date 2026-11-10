# Agent notes — AirFood

## Overview

Read-only API + PWA for the live Aramark canteen menu (Hamburg), served over plain HTTP
from the reverse-engineered Qnips/Firebase/Firestore chain. No browser scraping in this
repo (that variant lives in `browser-api/`).

| Path | What it is |
|---|---|
| `main.py` | FastAPI app: `/health`, `/api/stores`, `/api/menu`, `/api/product`, mounts `web/dist` at `/` |
| `qmenu_http.py` | HTTP backend: token chain + Firestore REST reads + response mapping |
| `web/` | PWA (Vite + one Svelte island), see `web/AGENTS.md` |
| `tests/` | pytest suite (unit tests mock `_firestore_get`/`_menu_id`) |
| `bruno/` | HTTP request collection (run against localhost:8000) |
| `skills/airfood/SKILL.md` | Agent skill for querying the API |
| `original_api.md` | Reverse-engineering evidence: portal bundle, auth chain, Firestore paths |
| `browser-api/` | Nested repo: browser-scraping variant (Playwright over CDP) |
| `render.yaml` | Render blueprint: one Docker service, Frankfurt, serves web + API on one URL |

## Commands

```sh
uv sync                                  # install deps
uv run pytest                            # tests
uv run uvicorn main:app --reload         # local API on :8000 (no dist/ -> API only)
docker compose up -d --build             # full stack incl. PWA, on :8000
cd bruno && npx @usebruno/cli run -r --env local   # API smoke requests
cd web && npm run dev                    # PWA dev server on :5173, proxies /api to :8000
```

## Conventions

- New logic that branches (parsing, mapping, errors) gets a unit test in `tests/`.
- User input is whitelisted (`STORES`, `DAY_NAMES`, `week` bounded int); never interpolate raw input into URLs.
- Errors: `ValueError` -> 422 (client's fault), `ScrapeError` -> 502 (upstream). Network/parse failures raise `ScrapeError`, never raw exceptions.
- Dates: store zone from the week doc (`TimeZoneId`); "today" in UTC. Past days are omitted, matching the portal.
- No new dependencies for a few lines of stdlib; keep the image distroless-compatible (no shell assumptions in Dockerfile).
- Update this file in the same commit as any change it describes.

## Deploy

- Render: New -> Blueprint -> this repo -> `render.yaml` (service `airfood`, region frankfurt). One URL serves `/` (PWA), `/api/*`, `/docs`, `/health`.
- Keep the free instance warm: Uptime Kuma monitor on `https://<service>.onrender.com/health`, every 5-10 min.
- Demo without API: branch `ghpages` builds `web/` with `VITE_USE_MOCK=true` and deploys to GitHub Pages via its own workflow.
- CORS: default `*`; tighten with `CORS_ORIGINS` when final domains are known.

## Docs index

- Humans: `README.md`
- Agents querying the API: `skills/airfood/SKILL.md`
- Portal internals / RE evidence: `original_api.md`
- Task spec: `task.md`
