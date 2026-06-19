# Grocery Helper — agent notes

Berlin grocery-deal finder: Python/FastAPI backend (scrapers → SQLite/Postgres →
API) + React Native (Expo) app. See [README.md](README.md) for the full picture.

## Layout
- `backend/` — FastAPI app + scrapers (`app/scrapers/`), classifier
  (`app/categories.py`), tests (`backend/tests/`, pytest).
- `mobile/` — Expo app (TypeScript); `src/screens/`, `src/components/`,
  `src/api.ts`, `src/storage.ts`.

## Common commands
- Backend: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8001`
- Backend tests: `cd backend && source .venv/bin/activate && python -m pytest -q`
- Mobile typecheck: `cd mobile && npx tsc --noEmit`
- Mobile run: `cd mobile && npx expo start` (open on the iOS simulator).
- Web run: `cd mobile && npm run web` (Expo Web / react-native-web; serves the
  **same** app at `http://localhost:8081`). `App.tsx` centers a max-width column on
  web; the backend already sends permissive CORS, so it talks to the local API.

## Important notes / gotchas
- **Local API port is 8001**, not 8000 (8000 is usually already taken on the dev
  machine). `mobile/.env` → `EXPO_PUBLIC_API_URL=http://localhost:8001`. The iOS
  simulator reaches the Mac via `localhost`; a physical phone needs the LAN IP.
- **Two sources × two chains, tagged `Offer.source` / `Store.chain`**: `coupon`
  (Lidl Plus app endpoints, `app/scrapers/lidl.py`) and `flyer`
  (meinprospekt weekly Prospekt, `app/scrapers/bonial.py`). `bonial.py` is a
  publisher-parameterized engine (`MeinprospektScraper`): `BonialScraper` =
  **Lidl** (publisher `DE-1013`, page `/lidl`), `ReweScraper` = **REWE**
  (publisher `DE-1062`, page `/rewe-de`). The flyer feed is location-gated and
  reuses the lat/lng the Lidl Plus lookup resolves; REWE is a **separate store**
  (`chain="rewe"`) reusing those PLZ coords (a Berlin PLZ → one brochure region).
  **REWE's flyer has no regular price** → most REWE offers have no `discount_pct`
  (they sink under discount-sort but the optimizer ranks by absolute price). Two
  chains push a Berlin PLZ to ~1300 offers, so `/api/offers` `limit` cap and the
  app's load are **2000** (not 1000); a 3rd chain → move search server-side
  (`q` param) rather than raising it again.
- **Offers are de-duplicated at serve time** (`app/dedup.py`, used by both
  `/api/offers` and `/api/categories` so list and chip counts agree). A chain
  publishes several weekly brochures, so the flyer feed repeats a product across
  them (distinct content ids → distinct `external_id`s in the DB), and a product
  can be in both a coupon and the flyer. `dedup_offers` collapses by
  `(store, normalized-name, price_cents)` — name norm unifies curly/straight
  apostrophes ("Butcher's"/"Butcher’s") — keeping the **richest** copy (has
  `price_per_unit`, then a discount, then flyer). Cut a Berlin PLZ ~1322→~738 live
  offers. The DB still stores the dups (serve-time only); a scrape-time
  reconcile/purge would also shrink the table but risks wiping real data on a
  sample-fallback, so it's deferred.
- **Nearby-stores directory is separate from deal scraping** (`app/services/
  store_locator.py`, `GET /api/nearby-stores`): finds the nearest branch of each
  allowlisted chain (lidl/rewe/edeka/aldi/netto/penny/kaufland) via **OpenStreetMap
  Overpass** — `node/way["shop"="supermarket"]` + haversine, brand-prefix
  normalization (Aldi Nord→aldi, Netto Marken-Discount→netto). `active` = chain in
  `ACTIVE_CHAINS` (the ones we scrape). Public Overpass instances 504 a lot → tries
  mirrors in order + caches per-area (24h) + returns `[]` on total failure. These
  are **not** persisted as `Store` rows; the app's "My stores" saved list lives
  client-side (`mobile/src/storage.ts`, key `myStores`, **one entry per chain** —
  the branch the user picked). `GET /api/nearby-stores?chain=<slug>` returns **every
  branch of one chain** near the PLZ (nearest first, wider 6 km radius, deduped
  node/way) — the app's "Change" picker (`StoresModal`); without `chain` it's the
  nearest-per-chain list as before. **The picker (`chain` set) centres on the PLZ's
  real centroid via Nominatim** (`plz_centroid`, cached), NOT the scraped-store
  coords: the scraped Store reuses the nearest *Lidl*, which can sit a district away
  (10115/Wilmersdorf → a Schöneberg Lidl ~3 km off), which buried the user's actual
  local Edeka past the 12-cap. The **general list keeps the scraped-store coords** so
  its Lidl/REWE stay consistent with the deals (deliberate split). Pure logic
  (`_select_nearest`, `_all_branches`, `plz_centroid` parsing) is fixture/fake-client
  tested — no live API in tests.
- **Outbound calls are counted** (`app/metrics.py` + `app/http.py`): every scraper/
  locator builds its httpx client via `tracked_client()`, whose request hook tallies
  each call by host. `GET /api/scrape-stats` (JSON) shows totals (since startup) +
  `recent` — the latest ~20 individual calls (newest first, each with a UTC
  timestamp + friendly source), so a standalone Overpass call (opening Stores)
  shows up too, not just scrape runs; `GET /stats` is an HTML dashboard for it
  (`app/stats_page.py`, served from `main.py`), rendering the recent-calls log with
  relative "Xs ago" times; it fetches on demand via a **Refresh** button (loads once
  on open, then no auto-poll). Counts are in-memory (reset on restart). **Reference numbers**: browsing = 0
  external calls; one scrape run = **7** (2 Lidl Plus + 5 meinprospekt: 2 publisher
  pages + ~3 brochure-pages, varies with active-brochure count); opening Stores = 1
  Overpass call; tapping **Change** = 1 Nominatim (PLZ centroid) + 1 Overpass, all
  cached 24h. New external client code should use
  `tracked_client` so it's counted.
- **Categorization is path-aware** (`app/categories.py`): for flyer offers,
  Bonial's `categoryPaths` is the primary signal (non-food level-1 node →
  household; product node → category); coupons + brand-only flyer food fall back
  to the keyword/brand layer. `category_path` is stored, so the recategorize
  backfill (`python -m app.scripts.recategorize` / `POST /api/recategorize`)
  reproduces results without re-scraping. Watch for substring traps (e.g. "li**mett**e")
  and flavour words ("Mango"/"Pfirsich") stealing categories — guard them.
- **Product sub-grouping within a category** (`app/product_group.py`): a *second*,
  coarser layer under `category` — `product_group(name, brand, category) ->
  (group_key, group_label)` keys an offer to a product (e.g. fruits → "avocado")
  from the **name** (the `category_path` leaf is too unreliable: "Aprikosen"→
  Steinobst, "Mix Tafeltrauben"→an attribute node, coupons→no path). Curated
  per-category keyword→German-label map, specific→generic (so "Seelachs" beats
  "Lachs"); only produce/meat/fish/cheese/dairy/bakery are mapped, everything else
  → `(None, None)`. Computed in the serializer → `OfferOut.group`/`group_label`
  (**no DB column / migration**, like `unit_price_cents`). The app renders a
  `SectionList` **only in a selected category** (not All/search): products with ≥2
  offers get a header and float up (`mobile/.../DealsScreen.tsx` `buildSections`,
  `components/GroupHeader.tsx`); singletons sink to a "More" bucket. Grouping makes
  category mis-classification *visible* (a peach-flavoured drink lands under
  "Pfirsich"), so it's a good lens for tuning `categories.py`.
- **Aggregators soft-throttle bursts** (marktguru, Bonial): they return empty
  after many quick requests. Scrape weekly with backoff; both scrapers fall back
  to sample data on failure.
- **System Python 3.9's old LibreSSL can't TLS-handshake with some hosts** (e.g.
  marktguru) under `httpx`; meinprospekt/Lidl Plus work fine. For ad-hoc probing
  of TLS-picky hosts use `/usr/bin/curl` (SecureTransport).
- **SQLite-under-a-running-server gotcha**: deleting/recreating `backend/grocery.db`
  while `uvicorn` runs leaves stale pooled connections serving inconsistent data.
  After re-seeding the file, touch a backend `.py`
  (`python3 -c "import os; os.utime('app/main.py', None)"`) to force a reload +
  fresh pool.
- **DB schema**: new `Offer` columns (`source`, `category_path`, `price_per_unit`,
  `loyalty_note`) need the table rebuilt — `create_all()` only creates missing
  *tables*, not columns. Dev: `ALTER TABLE offers ADD COLUMN …` (or delete
  `grocery.db`) then re-scrape; **Postgres needs a real migration** (no Alembic yet).
- **Per-unit price & loyalty bonus are display-only fields** pulled from data we
  used to discard: `Offer.price_per_unit` = the source's per-unit string
  ("1 kg = 13.33"), from the flyer `priceByBaseUnit` / Lidl `pricePerUnit`
  (formatted client-side by `mobile/src/format.ts` `fmtPricePerUnit`).
  `Offer.loyalty_note` = a REWE card bonus ("1,00 € Bonus"), parsed from an `OTHER`
  deal's description/conditions by `bonial.py` `_loyalty_note` (most bonuses lack
  the `isCard` flag, so match on the "€ Bonus" text, not `isCard`).
- **"Cheapest €/kg" sort** uses `OfferOut.unit_price_cents` — `app/unit_price.py`
  `unit_price_cents()` normalizes `price_per_unit` to cents per **kg or litre** on
  one comparable axis (German Grundpreis; per-`Stück`/`wl`/`m`/malformed → None).
  It's **computed in the serializer** (no DB column/migration); the app sorts the
  loaded set client-side (`DealsScreen` `SortToggle`), nulls sink to the bottom.
- **Missing Grundpreis is recovered at serve time** (`unit_price.py`
  `derive_price_per_unit(unit, price_cents)`, used by the serializer when
  `Offer.price_per_unit` is null): the flyer often omits the per-unit price for
  produce **sold per 1 kg / 1 l** (the price *is* the €/kg, e.g. "Klasse I 1 kg")
  and sometimes embeds the Grundpreis in the description ("…1 kg = 5.67 150 g"). It
  only fires on those two safe cases — a *second* quantity ("500 g 1 kg" where 1 kg
  is a base ref, "1 kg 20 Stück"), an approximate "Ca. 1,1 kg", or multi-variant
  ranges → None (a wrong €/kg is worse than none). Feeds the card display +
  `unit_price_cents`. Covers ~108 otherwise-blank flyer offers. A general
  divide-by-net-weight (e.g. "500 g" → ×2) is deferred — multipack "20 × 10 g" and
  "Ca." traps make it riskier.
- **Commits**: author as the user only — no `Co-Authored-By: Claude` trailer.
