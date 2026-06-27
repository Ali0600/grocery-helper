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
  (CI also runs `--cov=app`; add a `DB` migration drift check via `alembic check`).
- Backend lint: `cd backend && source .venv/bin/activate && ruff check .` (`--fix` to autofix)
- DB migration (after a model change): `cd backend && alembic revision --autogenerate -m "msg"`,
  review the file, commit. Runtime auto-runs `upgrade head` at startup (`app/migrations.py`).
- Mobile typecheck: `cd mobile && npx tsc --noEmit`
- Mobile tests: `cd mobile && npm test` (jest-expo; CI runs `npm test -- --ci`)
- Mobile lint: `cd mobile && npm run lint` (ESLint, `eslint-config-expo` flat config)
- Mobile run: `cd mobile && npx expo start` (open on the iOS simulator).
- Web run: `cd mobile && npm run web` (Expo Web / react-native-web; serves the
  **same** app at `http://localhost:8081`). `App.tsx` centers a max-width column on
  web; the backend already sends permissive CORS, so it talks to the local API.

## Important notes / gotchas
- **Local API port is 8001**, not 8000 (8000 is usually already taken on the dev
  machine). `mobile/.env` → `EXPO_PUBLIC_API_URL=http://localhost:8001`. The iOS
  simulator reaches the Mac via `localhost`; a physical phone needs the LAN IP.
  **`api.ts` defaults to the Render URL** (not localhost) when `EXPO_PUBLIC_API_URL` is
  unset, so device/OTA builds reach production out of the box — `.env` overrides it for
  local dev. This default is load-bearing because **`eas update` does NOT read eas.json's
  build-profile `env`** (Expo SDK 55+), so OTA bundles have no injected URL and fall back
  to it; eas.json's `env` only applies to `eas build`. A "Couldn't reach the API at
  localhost:8000" on a device = a build/OTA made before this default (rebuild fixes it).
- **Two sources × three chains, tagged `Offer.source` / `Store.chain`**: `coupon`
  (Lidl Plus app endpoints, `app/scrapers/lidl.py`) and `flyer`
  (meinprospekt weekly Prospekt, `app/scrapers/bonial.py`). `bonial.py` is a
  publisher-parameterized engine (`MeinprospektScraper`): `BonialScraper` =
  **Lidl** (publisher `DE-1013`, page `/lidl`), `ReweScraper` = **REWE**
  (publisher `DE-1062`, page `/rewe-de`), `EdekaScraper` = **EDEKA** (publisher
  `DE-220164`, page `/edeka`). The flyer feed is location-gated and reuses the
  lat/lng the Lidl Plus lookup resolves; REWE and EDEKA are **separate stores**
  (`chain="rewe"`/`"edeka"`) reusing those PLZ coords (a Berlin PLZ → one brochure
  region). **REWE's and EDEKA's flyers have no regular price** → most of their
  offers have no `discount_pct` (they sink under discount-sort but the optimizer
  ranks by absolute price). Three chains push a Berlin PLZ to ~1600 raw / **~1050
  deduped** offers, so `/api/offers` `limit` cap and the app's load are **2000**;
  a 4th chain (or a denser PLZ crossing 2000) → move search server-side (`q` param)
  rather than raising it again.
- **Offers are de-duplicated at serve time** (`app/dedup.py`, used by both
  `/api/offers` and `/api/categories` so list and chip counts agree). A chain
  publishes several weekly brochures, so the flyer feed repeats a product across
  them (distinct content ids → distinct `external_id`s in the DB), and a product
  can be in both a coupon and the flyer. `dedup_offers` collapses by
  `(store, normalized-name, price_cents)` — name norm drops apostrophes
  ("Butcher's"/"Butcher’s"), strips German quotes + a produce quality-grade
  ("…Avocado »Hass«, Kl. I" vs "…Avocado Hass"), and maps remaining punctuation to
  spaces, so cross-brochure spelling variants match — keeping the **richest** copy (has
  `price_per_unit`, then a discount, then flyer). Cut a Berlin PLZ ~1322→~738 live
  offers. The DB still stores the dups (serve-time only); a scrape-time
  reconcile/purge would also shrink the table but risks wiping real data on a
  sample-fallback, so it's deferred.
- **Nearby-stores directory is separate from deal scraping** (`app/services/
  store_locator.py`, `GET /api/nearby-stores`): finds the nearest branch of each
  allowlisted chain (lidl/rewe/edeka/aldi/netto/penny/kaufland) via **OpenStreetMap
  Overpass** — `node/way["shop"="supermarket"]` + haversine, brand-prefix
  normalization (Aldi Nord→aldi, Netto Marken-Discount→netto). `active` = chain in
  `ACTIVE_CHAINS` (lidl/rewe/edeka — the ones we scrape). Public Overpass instances 504 a lot → tries
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
  external calls; one scrape run = **~9** (2 Lidl Plus + ~7 meinprospekt: 3 publisher
  pages — Lidl/REWE/EDEKA — + ~4 brochure-pages, varies with active-brochure count);
  opening Stores = 1
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
  **Debugging gotcha: `OfferOut` does NOT expose `category_path`** — `/api/offers` always
  shows it as absent/None, so never infer "this offer has no path" from the API. To see the
  real stored path, query `offers.category_path` in the DB (or reason backwards: if
  `recategorize` is a no-op yet a brand/keyword fix "should" apply, the offer has a *path*
  winning at layer #3 — a mis-filed path needs a layer-#2 `_FORM_OVERRIDES` guard, not a
  brand-map entry; e.g. "Vilsa H2 Obst …" water filed under Obst).
  **`_PATH_MAP` was expanded from a live taxonomy survey** (beverage spirit/…marken
  nodes, bread types, produce, sausage subtypes, würzmittel/salatdressing, …) + more
  single-category brands → **"Other" ~11% → ~1%** (12/1056 live). The leaf is *often a
  brand* (Lidl/EDEKA dump into a `Marken > Marken Lebensmittel > {brand}` subtree), so
  the path only helps when an *intermediate* node is a real category; brand-leaf paths
  stay on the brand/keyword layers (multi-category house brands like Gut&Günstig /
  Deluxe / Dr.Oetker / Milbona are deliberately left there). To re-survey, fetch a
  publisher's brochure pages and tally `products[].categoryPaths`. **`classify` order
  (6 layers)**: non-food path→household, **`_FORM_OVERRIDES`** (limonade/saft/joghurt/
  chips — definitive *form* words that beat even a *mis-filed* food path, e.g. the source
  tags "Bananenchips" under Obst), food taxonomy node, brand map, **`_OVERRIDES`**
  (flavour words like sekt/choco — after the brand so Häagen-Dazs Chocolate stays frozen),
  keyword rules. **QA a category against its product images**: re-classify from the DB
  (don't re-scrape — `python -m app.scripts.recategorize` syncs stored rows to the current
  classifier), then build a Pillow contact-sheet of that category's `image_url`s and eyeball
  it (that's how 4 mis-filed "fruits" — a peach aperitif, banana chips, lemonade, a yogurt —
  were caught).
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
- **Brochure discovery is location-pinned via a cookie** (`bonial.py`
  `_location_cookie`, `_current_brochures`): meinprospekt's publisher page (`/rewe-de`
  etc.) picks which **regional** brochures to show from a `location` cookie it otherwise
  seeds from the **request's IP geo** — so without pinning, a Frankfurt-hosted Render and a
  Berlin laptop discover *different* brochures for the *same* PLZ (Render was serving
  Frankfurt REWE/EDEKA flyers to Berlin users, and counts differed by host). We send a
  `location={"lat","lng","zip","countryCode"}` cookie built from the scraped PLZ's coords
  (proven to override IP: a Munich-coord cookie returns Munich brochures from a Berlin IP),
  so discovery is correct + deterministic. The brochure *content* endpoint (`/pages`)
  already takes `lat`/`lng`; the cookie fixes the *list*. (REWE/EDEKA are regional; Lidl is
  national, so Lidl is unaffected.)
- **Offers are deduped at scrape time too** (`dedup.py` `dedup_scraped`, called in
  `run.py` `_upsert`): the publisher page can surface several overlapping brochures, so the
  same product repeats across them with distinct content ids → the **raw** scrape count was
  non-deterministic (Render ~1506 vs local ~1087 for one PLZ). Collapsing by
  `(normalized name, price)` per store before upsert makes the stored set + the reported
  `scraped` count depend only on distinct products. This is the scrape-time twin of the
  serve-time `dedup_offers`; serve-time dedup still runs (it also catches cross-*source*
  coupon/flyer dups, which scrape-time — per source — does not).
- **QA principle — check cross-environment parity for host-dependent data.** The
  location-pinning bug above hid for a while because the *same* scrape logic runs on the dev
  Mac (Berlin IP) and Render (Frankfurt IP), and outputs were only ever checked on **one host
  at a time** — each looked plausible; the mismatch only appears side-by-side (the user
  noticing iOS vs web). Lessons baked in here, apply them to any future source: (1) when
  output depends on host/IP/location, verify the **same input yields the same output from
  both local and Render** before trusting it — the hermetic fixture tests can't (no live
  host). (2) A **count that varies by host or run is a bug signal, not noise** — here it
  masked duplicate + wrong-region brochures; serve-time dedup made the app *look* fine, which
  hid it. (3) **Pin location end-to-end**: the content endpoint was lat/lng-gated but
  discovery wasn't — a half-pinned pipeline that read as complete (CLAUDE.md even claimed the
  feed was "location-gated"). (4) **"More rows" ≠ "better data"** — Render's extra offers
  were the wrong region, not a bonus.
- **System Python 3.9's old LibreSSL can't TLS-handshake with some hosts** (e.g.
  marktguru) under `httpx`; meinprospekt/Lidl Plus work fine. For ad-hoc probing
  of TLS-picky hosts use `/usr/bin/curl` (SecureTransport).
- **SQLite-under-a-running-server gotcha**: deleting/recreating `backend/grocery.db`
  while `uvicorn` runs leaves stale pooled connections serving inconsistent data.
  After re-seeding the file, touch a backend `.py`
  (`python3 -c "import os; os.utime('app/main.py', None)"`) to force a reload +
  fresh pool.
- **DB schema is Alembic-managed** (`backend/alembic/`, `app/migrations.py`): the app
  runs `alembic upgrade head` at startup (not `create_all`). A model change → `alembic
  revision --autogenerate -m "…"`, review, commit; CI `alembic check` fails if a model
  drifts from the migrations. env.py drives the URL from settings (one config for SQLite
  + Postgres) with `render_as_batch=True` so SQLite ALTERs work. A pre-Alembic DB (tables
  but no `alembic_version`, e.g. an old dev `grocery.db`) is **stamped** at head on first
  boot, not re-created — so existing DBs (and a persistent Postgres) upgrade cleanly.
  **Tests build schema via `create_all` directly** (in-memory), so they don't touch
  Alembic. The Dockerfile must `COPY alembic ./alembic` (runtime needs the scripts).
- **Per-unit price & loyalty bonus are display-only fields** pulled from data we
  used to discard: `Offer.price_per_unit` = the source's per-unit string
  ("1 kg = 13.33"), from the flyer `priceByBaseUnit` / Lidl `pricePerUnit`
  (formatted client-side by `mobile/src/format.ts` `fmtPricePerUnit`).
  `Offer.loyalty_note` = a REWE card bonus ("1,00 € Bonus"), parsed from an `OTHER`
  deal's description/conditions by `bonial.py` `_loyalty_note` (most bonuses lack
  the `isCard` flag, so match on the "€ Bonus" text, not `isCard`).
  `Offer.app_price_cents` = a chain's **app-coupon price** (EDEKA "App-Preis" 2,99 €,
  the Milka example), parsed by `bonial.py` `_app_price` from a `SPECIAL_PRICE` deal
  whose `conditions[].other` contains "app" — **app markers only** (APP-PREIS / NUR
  MIT APP / …); Payback / "6 für" multibuy / "ab 2 Kisten" bulk / day-only specials
  are skipped (not a simple per-item price). Shown as a yellow "App X,XX €" pill on
  the card (`OfferCard`); ~24 EDEKA offers/PLZ. Display-only (doesn't touch
  sort/optimizer — those keep the guaranteed flyer price).
- **"Cheapest €/kg" sort** uses `OfferOut.unit_price_cents` — `app/unit_price.py`
  `unit_price_cents()` normalizes `price_per_unit` to cents per **kg or litre** on
  one comparable axis (German Grundpreis; per-`Stück`/`wl`/`m`/malformed → None).
  It's **computed in the serializer** (no DB column/migration); the app sorts the
  loaded set client-side (`DealsScreen` `SortToggle`), nulls sink to the bottom. The
  `SortToggle` offers **3 modes** — *Lowest price* (`price_cents` asc), *Biggest discount*
  (`discount_pct` desc, default), *Cheapest €/kg* (`unit_price_cents` asc) — all via one
  `compareOffers(a,b,mode)` comparator reused by the flat list, the within-group order, and
  the "More" bucket (so "discount" ranks by % even inside a category, not by price).
- **Missing Grundpreis is recovered at serve time** (`unit_price.py`
  `derive_price_per_unit(unit, price_cents)`, used by the serializer when
  `Offer.price_per_unit` is null), three cases: (1) the Grundpreis is **embedded in
  the description** ("…1 kg = 5.67 150 g") → extract it; (2) the item is sold as a
  **single net weight/volume** → **divide** the price by that amount on the €/kg|€/l
  axis ("500-g-Schale" @ 1,49 € → "1 kg = 2.98", "2,5 l" → €/l, "Klasse I 1 kg" is
  just the num=1 case); (3) anything ambiguous → None (a wrong €/kg is worse than
  none). The division **guards the traps** (`_DIVIDE_TRAP` + a one-token rule): a
  multipack ("3x 400 ml", "20 × 10 g"), an approximate ("Ca. 1,1 kg"), a numeric
  range ("250-300 g", "1,2/1,1 kg"), or any *second* quantity incl. a count ("900 g
  30 Stück", "500 g 1 kg") → None; a lone hyphenated weight ("500-g-Schale") is fine
  because the range rule needs a digit on **both** sides of the separator. Feeds the
  card display + `unit_price_cents`; serve-time only (no DB column/migration), so it
  applies on Render right after deploy without a re-scrape. Lifts live €/kg coverage
  **~52% → ~69%** of offers (+~230).
- **Day-limited deals — per-offer validity** (`bonial.py` `_offer_validity`): a flyer offer
  can be on sale only certain days (Lidl Thu–Sat "Wochenend-Kracher", Mon–Fri, single-day).
  The real window is in `content.publicationProfiles[].validity` (`startDate`/`endDate`,
  UTC Berlin-midnight boundaries — convert with `zoneinfo("Europe/Berlin")`, `endDate` is
  *exclusive*); we read it (union of brochure-overlapping profiles, clamped) into
  `Offer.valid_from`/`valid_to` **instead of the whole-brochure window** — so a Thu–Sat deal
  no longer reads as valid all week, and the `/api/offers` `valid_to >= today` filter drops
  ended day-deals correctly. **No schema change** (reuses the date columns), but it's set at
  **scrape time** → Render needs a re-scrape (not just recategorize) to backfill. `tzdata` is
  a dep so the Berlin conversion is host-independent (slim Docker strips the system tzdb).
  `app/validity.py` derives **computed** `OfferOut.valid_days` ("Do–Sa"/"Fr") + `day_limited`
  (window < the Mon–Sat week) in the serializer; the app shows an orange day pill
  (`OfferCard`) + a session **"Special days"** toggle (`SpecialDaysToggle`, shown only when
  some offer is `day_limited`; filters client-side to `day_limited` offers — every non-week-long
  special, not the device date). Measured (10115):
  Lidl ~227 day-limited (Do–Sa/Mo–Fr/Do–Fr/Fr–Sa/Fr); REWE/EDEKA all full Mon–Sat.
- **Deployment**: backend is live on **Render** (free tier) at
  `https://grocery-helper-sw6c.onrender.com` via the IaC `render.yaml` Blueprint
  (Docker, `backend/Dockerfile`, binds `$PORT`, `/health` check). Render free tier
  **sleeps after ~15 min idle** → cold start re-runs the boot scrape (slow first
  request) and its SQLite is **ephemeral**, so startup `alembic upgrade head` rebuilds
  the schema from migrations every deploy — meaning **new `Offer` columns auto-apply on
  Render** (the migration runs there) while local dev applies them via the same upgrade
  (or a `grocery.db` recreate) + re-scrape. iOS /
  TestFlight config: `mobile/eas.json` (production profile; `EXPO_PUBLIC_API_URL` →
  the Render URL) + `mobile/app.json` (`ios.bundleIdentifier` `com.groceryhelper.berlin`,
  EAS project `@mhassan0600/grocery-helper`, `extra.eas.projectId`). `eas
  login`/`build`/`submit` are **user-run** (their Apple/Expo creds + build credits).
- **Deals are cached client-side** (`mobile/src/storage.ts` `dealsCache` **single key** +
  `DealsScreen`): the app shows the last good offers/cats/storeName for the PLZ
  **instantly**. **Flyers are weekly, so the cache is authoritative for the week**: a fresh
  cache (not past the cached week's Sunday) is served with **no backend call at all** — the
  app only fetches when there's no cache or the cache is stale, or on pull-to-refresh. So
  Render free-tier cold starts don't block the UI, the app works offline, and a typical
  mid-week open never touches the backend. Only the **last** PLZ is cached
  (one key, ~1 MB cap). Staleness = past the cached week's **Sunday** (`format.ts`
  `dealsStale`, the weekly flyer expiry), surfaced with a "may be expired" banner by
  `components/UpdateStatus.tsx`; a failed refresh keeps the cached list (no error screen).
  The full-screen spinner only shows on a true cold start (no cache for that PLZ).
  **Cold-start gotcha**: Render's ephemeral DB only boot-scrapes `DEFAULT_PLZ`, so
  `/api/offers` returns **`[]` for any other (unscraped) PLZ** until a scrape runs.
  `DealsScreen` `revalidate` therefore **scrapes on demand when the read is empty** (like
  `PlzModal` does via `api.scrape`) then refetches, and — critically — **never caches or
  displays an empty result over good data** (an empty cold-backend refresh used to wipe
  the deals + poison the cache). Fetches have AbortController timeouts (30s reads / 120s
  scrape) so a cold start fails fast instead of hanging.
- **Options view** (`mobile/src/components/OptionsModal.tsx`, ⚙ in the header): maintenance
  actions split **device** vs **server**. Device — *Clear cached deals & reload* (drops
  `dealsCache` then forces `revalidate(true)`, the fix for "deals won't update mid-week"
  since the weekly cache otherwise skips the backend) and *Reset all app data*
  (`storage.clearAllData` → `multiRemove` every key, then resets state to defaults / default
  PLZ). Server — *Re-scrape* (`api.scrape`, upsert) and *Wipe & re-scrape* (`api.resetDb` →
  **`POST /api/reset`**). Destructive actions use an **inline two-tap confirm** (not
  `Alert.alert`, which drops its buttons on react-native-web). `POST /api/reset` deletes
  **all** offers then re-scrapes one PLZ (unlike `/api/scrape`'s in-place upsert, so it also
  clears stale rows the scrape no longer touches); guarded by **`ADMIN_TOKEN`** *only when
  that env is set* (else open like `/api/scrape`); the app sends `EXPO_PUBLIC_ADMIN_TOKEN`
  if present. The wipe self-heals via the immediate re-scrape but comes back sparse on a
  sample-fallback (re-run when the source is reachable).
- **AI Recipes are offline-authored, OTA-shipped — NO runtime LLM/API** (`mobile/src/data/
  recipes.ts` + `RecipesModal`, "Recipes" header button). Deliberate per the user: no
  `ANTHROPIC_API_KEY`, no Render call, no `/api/*` endpoint. Recipes are authored **ahead of
  time by Claude Code** (the agent — not a metered key) from the current `grocery.db` deals +
  the always-have staples, bundled in the app, and shipped via the `eas-update.yml` OTA push.
  At runtime the app is fully offline: `mobile/src/recipes.ts` `resolveRecipe`/`filterRecipes`
  **reuse the Basket matcher** (`basket.ts` `bestMatch`) to tag each ingredient on-sale (matched
  an offer → live chain pill + price) / have (`staple:true` or in the user's always-have list)
  / buy, and filter by diet/cuisine/servings/only-on-sale/cheapest-€/kg. Always-have is seeded
  from `catalog.ts` staples (`storage.ts` `defaultAlwaysHave` / `STAPLE_KEYS`), editable +
  persisted (`alwaysHave` key; `recipePrefs` for filters). **Regenerate weekly** when flyers
  refresh: `python -m app.scripts.recipe_seed` (read-only candidate dump) → Claude Code
  rewrites `recipes.ts` → commit → OTA. Full workflow in `docs/recipes.md`. A `claude -p` CI
  generator is deferred (would need Claude Code auth in CI → breaks "no managed key").
- **CI/CD is GitHub Actions** (`.github/workflows/`): `ci.yml` (backend
  `ruff`+`pytest --cov`+`alembic upgrade head`/`alembic check`, mobile
  ESLint+`tsc`+`jest`, backend Docker build; on green `main` pushes a `deploy` job curls
  the Render deploy hook), `eas-update.yml` (OTA via `eas update --branch production` on
  `mobile/**` pushes), `scrape.yml` (weekly cron → `POST /api/scrape`, retries 3× and
  opens/comments a `scrape-failure` issue on total failure). `dependabot.yml` auto-bumps
  pip/npm/actions weekly (minor+patch grouped). Deploy + OTA + **Codecov upload**
  **skip gracefully** until their secrets exist (`RENDER_DEPLOY_HOOK_URL`, `EXPO_TOKEN`,
  `CODECOV_TOKEN`), so CI stays green; gated deploy assumes Render **auto-deploy is off**. CI Python is
  **3.12** (Dockerfile/Render) but the local venv is **3.9** — `backend/ruff.toml` targets
  `py39` so lint never pushes 3.10+ syntax that breaks local. **Lint must pass** before a
  push: `ruff check .` + `npm run lint`; `react-hooks/set-state-in-effect` is intentionally
  a **warning** (legit modal fetch/reset effects), keep real errors at zero. OTA only
  reaches a build embedding `expo-updates` at the matching `runtimeVersion` (app.json
  `appVersion` policy) → bump `expo.version` when native deps change.
- **In-app OTA prompt** (`mobile/src/useOtaUpdates.ts`, called once in `App.tsx`): checks
  for an EAS Update on launch + on every app foreground and, if one is ready, downloads it
  and alerts the user to reload now (`Updates.reloadAsync`). Inert in dev / Expo Go / web
  (`__DEV__` / `Platform.OS` / `Updates.isEnabled` guards), best-effort, once per session.
  Only fires in a build embedding `expo-updates` at the matching `runtimeVersion`.
- **Commits**: author as the user only — no `Co-Authored-By: Claude` trailer.
