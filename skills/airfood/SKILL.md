---
name: airfood
description: Query the live Aramark catering menu (Hamburg Kreetslag/Fuhlsbüttel/TUHH/ZAL) served by the AirFood API. Use when the user asks what is on the menu today, what dishes are available, prices, allergens, dietary tags, or for a dish recommendation.
---

# AirFood menu skill

Base URL: `http://localhost:8000` (override with `AIRFOOD_BASE_URL`). Interactive docs: `/docs`.

## Endpoints

- `GET /api/stores` — list of the 10 menu stores (`name`, `menu`).
- `GET /api/menu?store=<name>&week=<1-53>&day=<Weekday>` — menu JSON. All params optional; defaults: store `Airbus Finkenwerder`, current ISO week, all remaining days of that week (past days are omitted by the source).
- `GET /health`

## Response shape

```json
{"store": "...", "menu": "...", "week": "CW: 45",
 "days": [{"label": "Tue. 03.11.", "weekday": "Tuesday",
           "meals": [{"name": "...", "category": "...", "price": "1.80", "currency": "EUR",
                      "price_options": [{"label": null, "amount": "9.25", "currency": "EUR"}],
                      "allergens": ["A", "C", "G"],
                      "tags": [{"name": "Vegetarian", "image_url": "..."}],
                      "image_url": "..."}]}]}
```

## Typical questions

- "What's the menu today?" → `GET /api/menu?store=Airbus Finkenwerder&day=<today's weekday>`, summarize `days[0].meals` by category with prices.
- "What can I eat at ZAL?" → `GET /api/menu?store=ZAL TechCenter`; note `price_options` (e.g. standard vs `intern` price) — mention both.
- "Recommend a dish" → fetch today's menu, prefer meals with tags like `Vegetarian` if the user asks for vegetarian, and avoid meals whose `allergens` match a user-stated allergy (allergen codes are portal labels like A/C/G).
- "Any soup?" → filter meals whose `category` or `name` contains "soup"/"Suppe".

Notes: weeks are a rolling set (current/upcoming only; unknown week → 422). Dish names embed the ingredient text after `|` — the portal exposes no structured ingredient list. A store with no data returns `{"days": []}`.
