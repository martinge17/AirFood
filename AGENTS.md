# Agent notes

- `task.md` is the project specification; `original_api.md` records the reverse-engineered portal API.
- This repo is HTTP-only: `qmenu_http.py` replicates the portal's Qnips/Firebase token chain and reads Firestore REST v1 (`Release/en-US/StoreMetas`, `.../Menus/{id}/Years/{y}/Weeks/{cw}`). The browser-scraping variant is the nested repo `browser-api/`.
- Agent-facing skill for querying the API: `skills/airfood/SKILL.md`.
- Setup/checks: `uv sync`, `uv run pytest`, `uv run uvicorn main:app --reload`. Docs at `/docs`; Bruno: `cd bruno && npx @usebruno/cli run -r --env local`.
- Run: `docker compose up -d --build` (or `docker build -t airfood . && docker run --rm -p 8000:8000 airfood`). The image is multi-stage on Chainguard distroless (`cgr.dev/chainguard/python`), exec-form CMD, nonroot, no shell/package manager.
- The portal exposes only its current/upcoming weeks; past days are omitted (the HTTP backend filters them by the week doc's `TimeZoneId`). Do not imply historical-week support or invent structured ingredient lists.
