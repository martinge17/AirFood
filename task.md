# AirFood

## Goal

Provide an API that returns the meals shown by the Aramark Catering Portal as JSON, so they can later be used to plan weekly lunches and dinner alternatives.

Primary menu: <https://aramark.cateringportal.io/menu/Kantine%20Hs.%2018/Kantine%20Hs.%2018,%20HH-Finkenwerder>

The portal allows users to choose a store, week, and day, and displays meal details such as name, ingredients, price, and image.

## Initial scope

- Fetch menu data for a selectable menu store and available week/day, and expose it through the project's own API.
- Represent each meal as a JSON object containing the portal's displayed name, category, price options, allergen codes, dietary tags, and image URL when present. Preserve unavailable values; ingredient-like text is part of the displayed name and is not a structured ingredient list.
- Support the ten menu choices documented in `original_api.md`. Default to Airbus Finkenwerder and preserve the portal's menu route style. Stores without a menu selector entry are directory-only, not scrape targets.
- Create a Bruno collection that exercises the API's supported options.

## Stack

- FastAPI
- `uv` for Python project and dependency management
- Bruno for API requests and examples

## Current API

- `GET /api/stores` lists menu-enabled store choices.
- `GET /api/menu?store=Airbus%20Finkenwerder&week=45` returns all enabled days for a portal-available calendar week.
- Add `&day=Tuesday` to return one weekday. The portal controls which weeks and days are currently selectable.
- `GET /docs` provides interactive OpenAPI documentation.

Run locally with `uv sync`, `uv run playwright install chromium`, and `uv run uvicorn main:app --reload`. Or build and run with Docker: `docker build -t airfood .` then `docker run --rm -p 8000:8000 airfood`.

## Later goal

Use the menu data to generate a weekly meal schedule: suggested lunch dishes for each day and dinner proposals from other food sources. This is a future capability, separate from the initial menu-fetching API.
