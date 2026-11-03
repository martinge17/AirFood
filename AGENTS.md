# Agent notes

- `task.md` is the project specification; `original_api.md` records portal behavior and verified menu/store options.
- Two backends: `backend=http` (default selectable via `AIRFOOD_BACKEND` or `?backend=`) reads the portal over plain HTTP using the reverse-engineered Qnips/Firebase chain in `qmenu_http.py` — no browser at all; `backend=browser` renders the Angular SPA via Playwright over CDP (`BROWSER_WS`, `BROWSER_WS_TOKEN`; local Chromium fallback, run `uv run playwright install chromium` first). Compose runs the API plus an Obscura browser service on the host network.
- Setup/checks: `uv sync`, `uv run pytest`, `uv run uvicorn main:app --reload`. API docs are at `/docs`; Bruno requests are under `bruno/` and run with `cd bruno && npx @usebruno/cli run -r --env local`.
- Build/run the stack with `docker compose up -d --build` (API on :8000 + Obscura CDP on :9222), or standalone `docker build -t airfood .` + `docker run --rm -p 8000:8000 airfood`. The image is multi-stage: no `uv`, dev deps, or Chromium inside it, so use `AIRFOOD_BACKEND=http` for the standalone container.
- The portal exposes only its current/upcoming weeks in the selector; past disabled days are omitted. Do not imply historical-week support or invent structured ingredient lists that the portal doesn't expose.
