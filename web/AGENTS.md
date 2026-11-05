# Agent notes — web/ (PWA)

Vite + Svelte 5, single screen (`src/App.svelte`), built to `dist/` and mounted at `/`
by the API container. PWA via `vite-plugin-pwa`.

## Commands

```sh
npm install
npm run dev        # :5173, proxies /api -> http://127.0.0.1:8000
npm run build      # -> dist/ (this is what the Docker image serves)
```

## Conventions

- One Svelte island; keep JS small (currently ~20 kB gzip). No new UI framework.
- API base: relative `/api/*` by default; `VITE_API_URL` at build time for static hosting;
  `VITE_USE_MOCK=true` (ghpages branch, ships real `src/mock.js`) for the Pages demo.
- Service worker must not swallow API/docs navigations — keep `navigateFallbackDenylist` in `vite.config.js`.
- Cards must render consistently with or without image/ingredients/sticker (fixed grid).
- `web/.agents/skills/frontend-design` is the design reference (installed skill, untracked).
