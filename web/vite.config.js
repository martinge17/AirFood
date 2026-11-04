import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  plugins: [
    svelte(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icons/icon.svg"],
      manifest: {
        name: "AirFood",
        short_name: "AirFood",
        description: "Live Aramark canteen menu",
        theme_color: "#1e5c48",
        background_color: "#f6f4ef",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "icons/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
          { src: "icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icons/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
      workbox: {
        navigateFallback: "/index.html",
        // never serve the app shell for API/docs/health navigations
        // (workbox tests these against the full href, so no ^ anchor)
        navigateFallbackDenylist: [/\/api\//, /\/redoc/, /\/docs/, /\/health/],
      },
    }),
  ],
  build: { outDir: "dist" },
});
