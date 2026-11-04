# Aramark portal: source/API notes

Inspected on 2026-11-03. The public menu URL is:

`https://aramark.cateringportal.io/menu/Kantine%20Hs.%2018/Kantine%20Hs.%2018,%20HH-Finkenwerder`

## Store options

The portal was inspected in Chromium through `agent-browser` with desktop and Android Chrome user agents. The menu selector contains these ten choices; changing the selection produced the corresponding menu route and live menu:

| Store selector label | Menu name | URL path after `/menu/` |
|---|---|---|
| Airbus Finkenwerder | Casino HH-Finkenwerder | `Airbus Finkenwerder/Casino HH-Finkenwerder` |
| Betriebsrestaurant Fuhlsbüttel | Betriebsrestaurant HH-Fuhlsbüttel | `Betriebsrestaurant Fuhlsbüttel/Betriebsrestaurant HH-Fuhlsbüttel` |
| Bistro Halle 9 | Bistro Halle 9 | `Bistro Halle 9/Bistro Halle 9` |
| Casino | Casino HH-Finkenwerder | `Casino/Casino HH-Finkenwerder` |
| Elbblick | Elbblick HH-Finkenwerder | `Elbblick/Elbblick HH-Finkenwerder` |
| Kantine Hs. 18 | Kantine Hs. 18, HH-Finkenwerder | `Kantine Hs. 18/Kantine Hs. 18, HH-Finkenwerder` |
| Marché | Marché HH-Finkenwerder | `Marché/Marché HH-Finkenwerder` |
| Sharklet Hs. 100 | Sharklet Hs.100, Daily Menu | `Sharklet Hs. 100/Sharklet Hs.100, Daily Menu` |
| TUHH | Airbus TU | `TUHH/Airbus TU` |
| ZAL TechCenter | ZAL TechCenter | `ZAL TechCenter/ZAL TechCenter` |

The site’s separate **Stores** directory also lists **Food Trucks** and **Shops und Coffee Points** at Kreetslag 10. Neither appears in the menu selector, so no menu URL was observed for them. The directory showed these locations (all in Hamburg): Airbus Finkenwerder — Kreetslag 10, 21129; Betriebsrestaurant Fuhlsbüttel — Weg beim Jäger 150, 22335; Bistro Halle 9 — Kreetslag 10, 21129; Casino — Kreetslag 10, Haus 25, 21129; Elbblick — Kreetslag 10, Haus 249, 21129; Food Trucks — Kreetslag 10, 21129; Kantine Hs. 18 — Kreetslag 10, Kantine Haus 18, 21129; Marché — Kreetslag 10, Haus 61, 21129; Sharklet Hs. 100 — Kreetslag 10, Haus 100, 21129; Shops und Coffee Points — Kreetslag 10, 21129; TUHH — Neßpriel 5, 21129; ZAL TechCenter — Hein-Saß-Weg 22, 21129.

Paths are URL-encoded in actual links (for example, spaces become `%20`, and `Marché` becomes `March%C3%A9`). Airbus Finkenwerder and Casino are distinct selector choices even though both use the menu name “Casino HH-Finkenwerder”.

## How the portal serves menus

The menu page is an Angular single-page application: a plain HTTP request returns only its shell, while a JavaScript-enabled browser renders menu data. The application reads store/menu data from Firebase Firestore (WebChannel listener requests), after obtaining Firebase configuration/auth through the portal. The client uses the following Firestore document/collection paths (the `Environment` value and language are configured by the application):

- Stores: `{Environment}/{language}/StoreMetas` (the client flattens each document's `Stores` array)
- Store details: `{Environment}/{language}/Stores/{storeId}`
- Menu details: `{Environment}/{language}/Menus/{menuId}`
- Weekly menu: `{Environment}/{language}/Menus/{menuId}/Years/{year}/Weeks/{week}`
- Days within a week: `{Environment}/{language}/Menus/{menuId}/Years/{year}/Weeks/{week}/Days`, filtered by `WeekDay`

The client also refers to an invariant menu path for preorder slot statistics; it is not needed for meal listings. Chromium via `agent-browser` successfully rendered both supplied menu URLs, the store list, and meal details. The same menu loaded with desktop and Android Chrome user agents. `agent-browser` needs `--args '--no-sandbox'` in this container.

## Reverse-engineered HTTP data source (no browser needed)

The SPA bundle (verified against live traffic on 2026-11-03) authenticates and reads in plain HTTP:

1. `GET https://apps-live-eu.qnips.com/cons/api/FirebaseInfo` with headers `Authorization: 007774ebf508aa88e44eab2baf833ae97c` (the bundle's default auth header), `App-Brand: aramark`, `Response-Version: v3` → returns a Firebase `CustomToken`, `Environment: Release`, `Region: europe-west1`. The Firebase web config is embedded in the bundle (project `q-aramark`, apiKey `AIzaSyBC7KHOACAPWb0DwSceR3ZdoO-BUMfgoSw`).
2. `POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=<apiKey>` with body `{"token": <CustomToken>, "returnSecureToken": true}` → `idToken` + `refreshToken` (1 h lifetime; `returnSecureToken` is required to get the refresh token).
3. `GET https://firestore.googleapis.com/v1/projects/q-aramark/databases/(default)/documents/<path>` with `Authorization: Bearer <idToken>`.

Concrete read paths (language is `en-US`, not `en`; menu ids are numeric):

- `Release/en-US/StoreMetas` — each doc's `Stores` array maps `StoreId` → `Menus` (with `Id`, `Name`, `ShowInCateringPortal`). This is how URL menu names resolve to numeric menu ids (e.g. "Casino HH-Finkenwerder" → `12246`, "ZAL TechCenter" → `12254`).
- `Release/en-US/Menus/{menuId}/Years/{isoYear}/Weeks/{isoWeek}` — the week doc. Days are **inline** in the week doc's `Days` array when `HasDayDocs` is false (as for these menus); the `/Days` subcollection is empty in that case. Each day has `Date` (UTC midnight), `WeekDay`, `Categories[].Products[]` with `Name`, `Prices[]` (`Price` double + `LocalizablePrice.CurrencyCode`, optional `Label` such as "intern"), `Allergens`/`Additives` (id refs into the week-level `Allergens`/`Additives` tables, which carry `Label` like `A1`/`G`), `CustomTags` (name + icon URL), `PictureUrl`. The week doc also carries `TimeZoneId` (e.g. `Europe/Berlin`); the portal disables days before "today" in that zone.
- `Release/invariant/Stores/{storeId}` also exists but only stores the `StoreId`; not needed for menus.

Unauthenticated REST reads return `PERMISSION_DENIED`/`UNAUTHENTICATED`; collection-group queries return 403. The token chain above is what the SDK uses (iss `https://securetoken.google.com/q-aramark`, `sub` set) and is replicated in `qmenu_http.py` (`backend=http`).

## Observed and scraped menu data

On 2026-11-03, the Airbus Finkenwerder menu showed calendar week 45, selectable weekdays, menu sections, dishes, allergen codes, displayed prices, dietary tags, and product images. Opening “Minestrone | Italian vegetable soup” showed price €1.80 and allergen descriptions for A/A1/C/G, plus a Nutritional Information tab. The portal doesn't expose a separate structured ingredient list; preserve the full displayed dish name rather than splitting it into guessed ingredients.

The scraper returns these fields for each dish: `name`, `category`, `price`, `currency`, `price_options`, `allergens`, `tags`, and `image_url`. `price_options` preserves alternatives such as the ZAL menu's standard €9.25 and `intern` €7.25 prices. Missing prices/images remain `null`/empty instead of being fabricated. Example live result: “Minestrone | Italian vegetable soup”, category `Suppentopf`, `price: "1.80"`, `currency: "EUR"`, allergens `["A", "C", "G"]`, tag `Vegetarian`, and a portal image URL.

## AirFood API behavior

- `GET /api/stores` returns the ten menu-selector choices above; directory-only Food Trucks and Shops und Coffee Points are excluded.
- `GET /api/menu?store=Airbus%20Finkenwerder&week=45` scrapes all selectable days for that available week. `day=Tuesday` filters to one day; omitted `store` defaults to Airbus Finkenwerder.
- Week availability is controlled by the live portal selector (currently a rolling set, not arbitrary historical weeks). Disabled/past day tabs are omitted. Invalid store/day/week selections return a client error; portal/browser failures return 502.
- The `week` output is the portal label (`CW: 45`), and day labels are portal display labels; they are not guaranteed to include a year.
- This service uses only the plain-HTTP Firestore chain above (no browser). The earlier browser-scraping variant (Playwright over CDP, Obscura) is kept in the nested repo `browser-api/`; both returned identical fields.

## Scraping implications

- Use a JavaScript-capable browser or the authenticated HTTP flow above; a plain HTML request and anonymous REST reads are insufficient.
- Store/menu options above were read from the live UI. They can change; do not treat directory entries without a selector menu as scrapeable menus.
- Portal menus vary by week/day and can omit fields. Do not infer missing meal properties or hard-code sample menu data as production behavior.
- Verified against the original portal on 2026-11-03: the API returned the live Tuesday CW 45 menu and matched the visible Minestrone dish, price, allergens, tag, and image. All ten selector stores returned a Tuesday menu in that week; ZAL confirmed multiple price options.
