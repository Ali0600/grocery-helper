# Grocery Helper

Find the best weekly grocery deals near you in Berlin. The app scrapes the
weekly offers ("Angebote") from local supermarket chains, normalizes and
categorizes them, computes the **% discount** for every item, and helps you
build the cheapest basket across one or two stores.

> **Status:** v1 in progress. **Live Lidl + REWE + EDEKA offers** + API + the React
> Native app work end-to-end — real Berlin prices, resolved from your postal
> code via the Lidl Plus endpoints and the meinprospekt weekly-flyer feed. Three
> chains make the basket optimizer and per-product price comparison meaningful.
> The **backend is deployed on Render** (HTTPS), and the iOS app is wired for
> **EAS → TestFlight**. See [Deploy](#deploy-to-render-free-https-for-testflight)
> and [Roadmap](#roadmap).

## Highlights

- **Automated grocery-deal ETL pipeline** — scrapes and normalizes weekly offers
  from multiple German retail sources into a relational database on a scheduled,
  containerized cron job, computing per-item discount percentages.
- **Reverse-engineered a retailer's private mobile API** — geolocates the nearest
  store from a postal code and pulls live structured offer data (current +
  regular price) from Lidl's app endpoints, yielding exact discount percentages.
- **Discount-ranking & multi-store basket optimization API** — a FastAPI service
  exposing endpoints to filter offers by category, rank by % discount, and
  compute the cheapest basket across one or two stores.
- **In-app shopping-list basket with cross-store price optimization** — users build
  a grocery list (bilingual quick-add: "Strawberry" or "Erdbeere") that is matched
  **per-product** against the live deal set entirely client-side, surfacing the
  cheapest offer per item and a store-by-store shopping plan with the savings vs.
  shopping at a single store — deterministic keyword matching (no LLM), reusing the
  already-loaded in-memory faceted dataset for instant results.
- **Offline LLM-authored recipe generator (zero runtime API cost)** — an AI "Recipes"
  feature that suggests meals from the week's on-sale items plus user-defined "always-have"
  staples. Recipes are **authored offline by an LLM from the live deal database** and shipped
  to devices **over-the-air** (no runtime model call, no API key/secret, no server cost); the
  app renders them fully offline and reuses the deterministic basket matcher to show each
  ingredient's real on-sale price and flag what's on-sale vs a pantry staple vs to-buy.
  Customizable by diet, cuisine, servings, on-sale-only, and cheapest-€/kg.
- **Cross-platform client (iOS + web, one codebase)** — a React Native (Expo)
  app consuming the API to browse local deals by category, sorted by savings;
  the same code runs in the browser via Expo Web / react-native-web
  (`npm run web`).
- **Containerized, deployable stack** — Dockerized backend with Docker Compose +
  PostgreSQL, designed for CI/CD deployment to a PaaS with scraper health
  monitoring and alerting.
- **Versioned database migrations (Alembic)** — schema changes are tracked migrations
  (one config covering SQLite dev + PostgreSQL prod, applied automatically at startup),
  replacing ad-hoc table creation so columns can evolve safely on a persistent database;
  a legacy pre-migration database is auto-stamped rather than re-created.
- **CI/CD pipeline (GitHub Actions)** — parallel test / lint / type-check /
  Docker-build gates on every push and PR (backend `pytest` **with coverage
  reporting** + mobile **Jest**, ruff, ESLint, `tsc`), green-gated production deploys
  to Render via deploy hooks, over-the-air mobile delivery through EAS Update, and a
  scheduled weekly data-refresh cron that **retries and opens a GitHub issue on
  failure** — with least-privilege permissions, dependency caching, concurrency
  control, and **Dependabot** automated dependency updates.
- **Automated test suite** — 264 backend unit tests (pytest) covering the scrapers,
  classifier, dedup, unit-price and validity logic, plus a React Native **Jest** suite
  for the app's pure business logic (basket matching, recipe filtering, €/formatting,
  catalog trap-guards); a model-vs-migration **drift check** (`alembic check`) fails CI
  if the ORM and schema diverge.
- **Multi-retailer ingestion across heterogeneous sources** — a single
  publisher-parameterized engine normalizes two German chains (Lidl + REWE) from
  three feeds (a private mobile coupon API and structured weekly-flyer data) into
  one schema, tagged by chain/source, powering a cross-store basket optimizer.
- **Geospatial store discovery** — an OpenStreetMap Overpass integration that
  finds the nearest branch of each major chain around a postal code (haversine
  ranking, multi-mirror failover, response caching), powering an in-app
  "nearby stores" directory with a saved-stores list.
- **Resilient scraping design** — store-agnostic normalization layer and
  fall-back data paths so a single upstream change never takes the app down.
- **In-app maintenance/admin controls** — an Options panel exposing client- and
  server-side data-lifecycle actions (clear on-device cache, full app reset,
  on-demand re-scrape, and a guarded database wipe-and-reseed via `POST /api/reset`
  gated by an optional `ADMIN_TOKEN`) — giving an operator one-tap recovery from
  stale cache or bad data without a redeploy.
- **Day-aware deal validity** — parses each offer's true on-sale window from a
  per-record validity field the feed buries (timezone-correct via `zoneinfo`), so
  day-limited specials (e.g. weekend-only deals) are badged with their days and
  filterable to "valid today", and ended specials expire correctly instead of
  lingering for the whole flyer week.
- **Outbound-call observability** — every request to an upstream site is
  instrumented (httpx event hooks) and tallied by source/host, plus a timestamped
  log of the latest calls, exposed at `GET /api/scrape-stats` with a live `/stats`
  dashboard — to keep an eye on scrape volume and avoid tripping the sites' burst
  throttling.
- **Structured logging & error tracking** — stdlib structured logging to stdout
  surfaces previously-silent scraper/locator failures (a degradation to fallback data
  is now logged, not hidden), with opt-in **Sentry** error tracking that auto-captures
  unhandled API exceptions when a DSN is configured (and is a no-op otherwise).

## Architecture

```
 Rewe API   Lidl API
     \         /
      v       v
 Scheduled scrapers   (weekly cron, retries)
        |
 Normalize + categorize + compute discount %
        |
   PostgreSQL  (stores, offers, categories)
        |
     FastAPI   (rank by %, store optimizer)
        |
 React Native (Expo) app
```

## Tech stack

| Layer      | Choice                                            |
| ---------- | ------------------------------------------------- |
| Mobile app | React Native (Expo), TypeScript                   |
| Backend    | Python, FastAPI, SQLAlchemy 2.0, Pydantic v2      |
| Database   | SQLite (local dev) / PostgreSQL (prod)            |
| Infra      | Docker, Docker Compose, PaaS (Railway/Render/Fly) |

## Repository layout

```
grocery-helper/
├── backend/            # FastAPI app + scrapers
│   └── app/
│       ├── api/        # HTTP routes
│       ├── core/       # config
│       ├── scrapers/   # per-chain scrapers + orchestration
│       ├── services/   # basket optimizer
│       ├── categories.py  # German-keyword product classifier
│       ├── models.py   # SQLAlchemy ORM models
│       └── main.py     # app entrypoint (lifespan: create tables + seed)
├── mobile/             # Expo app (added next)
└── docker-compose.yml  # Postgres + API for prod-like runs
```

## Running the backend (local, zero setup)

Local dev uses SQLite and seeds sample data automatically on first start — no
database to install.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open <http://localhost:8000/docs> for the interactive API, or try:

```bash
# Top deals overall, ranked by % discount
curl 'http://localhost:8000/api/offers?sort=discount&limit=5'

# Only beef offers
curl 'http://localhost:8000/api/offers?category=beef'

# Cheapest basket across 2 stores for a few categories
curl -X POST http://localhost:8000/api/optimize \
  -H 'content-type: application/json' \
  -d '{"categories":["beef","butter","fruits"],"store_count":2}'
```

### Run with Docker + Postgres (prod-like)

```bash
docker compose up --build
```

### Deploy to Render (free HTTPS, for TestFlight)

The backend ships an **Infrastructure-as-Code** [`render.yaml`](render.yaml)
Blueprint that deploys [`backend/Dockerfile`](backend/Dockerfile) as a Render web
service with a free managed HTTPS URL (`https://<name>.onrender.com`) — which is what
the iOS/TestFlight build talks to (a real device can't reach `localhost`, and iOS
requires HTTPS). Apply it via the Render dashboard → **New → Blueprint** (it reads
`render.yaml` from the repo). The container binds to Render's `$PORT`; `/health` is
the health check. The mobile production build points at this URL via
`EXPO_PUBLIC_API_URL` in [`mobile/eas.json`](mobile/eas.json).

> Free-tier note: the instance sleeps after ~15 min idle and cold-starts on the next
> request (the app re-seeds via a scrape on boot, so the first call after a sleep is
> slow). For durable data, attach a Render Postgres / persistent disk and set
> `DATABASE_URL` (the app already supports Postgres — see `docker-compose.yml`).

### Build for iOS / TestFlight (EAS)

```bash
cd mobile
eas login                              # your Expo account
eas init                               # links the EAS project
eas build -p ios --profile production  # cloud build (first run sets up Apple signing)
eas submit -p ios --latest             # upload the .ipa to TestFlight
```

Config lives in [`mobile/eas.json`](mobile/eas.json) (remote auto-incrementing build
numbers) and `mobile/app.json` (`ios.bundleIdentifier`). Set
`EXPO_PUBLIC_API_URL` in `eas.json` to your deployed backend URL before building.

## API

| Method | Path              | Purpose                                          |
| ------ | ----------------- | ------------------------------------------------ |
| GET    | `/api/offers`     | Offers; filter by `category`/`chain`/`plz`/`min_discount`, `sort=discount\|price` |
| GET    | `/api/categories` | Categories that currently have offers, w/ counts |
| GET    | `/api/stores`     | Known stores                                     |
| GET    | `/api/nearby-stores` | Nearest branch of each major chain near a PLZ (OSM); `active` flag for chains we scrape |
| POST   | `/api/optimize`   | Cheapest basket across 1–2 stores                |
| POST   | `/api/scrape`     | Re-run scrapers on demand (dev)                  |
| POST   | `/api/recategorize` | Re-apply the classifier to stored offers (dev) |
| GET    | `/api/scrape-stats` | Outbound calls to the scraped sites, by source/host (total + a timestamped recent-calls log); on-demand dashboard at `/stats` (Refresh button) |

## Scrapers

Two sources feed each Lidl store, tagged by `Offer.source`:

**Lidl Plus coupons** (`source="coupon"`) —
[`lidl.py`](backend/app/scrapers/lidl.py): resolves the nearest store for a postal
code via the Lidl Plus store-autocomplete endpoint, then pulls that store's app
coupons from `offers.lidlplus.com` (clean prices + exact discounts; ~50 items).
Endpoints adapted from
[EvickaStudio/lidl-discounts](https://github.com/EvickaStudio/lidl-discounts).

**Weekly Aktionsprospekt** (`source="flyer"`) —
[`bonial.py`](backend/app/scrapers/bonial.py): the full printed weekly leaflet via
meinprospekt (a Bonial property). Discovers Lidl's current brochure from the
publisher page (`__NEXT_DATA__`) using the store's coordinates, then pulls ~430
**structured** offers — name, brand, `SALES_PRICE` + `REGULAR_PRICE` (→ exact %),
image, validity. No OCR needed; the data is already structured. Runs weekly with
backoff (Bonial soft-throttles bursts). Both feeds fall back to sample data so the
app stays up.

**REWE weekly flyer** (`source="flyer"`, `chain="rewe"`) — the same
[`bonial.py`](backend/app/scrapers/bonial.py) engine, parameterized for REWE's
meinprospekt publisher (`DE-1062`, "Dein Markt"). Reusing the structured flyer
pipeline sidesteps REWE's Cloudflare-gated app API (`mobile-api.rewe.de`)
entirely. ~400 structured offers with names, brands, images, and `categoryPaths`
attach to a separate REWE store, giving the optimizer a real second chain to
compare. Caveat: REWE's flyer carries no struck-through "old" price, so most REWE
items show a price (and per-unit price) **without a % discount** — the optimizer
ranks by absolute price, so this doesn't affect it.

**EDEKA weekly flyer** (`source="flyer"`, `chain="edeka"`) — the same engine again
for EDEKA's national meinprospekt publisher (`DE-220164`). ~300 structured Berlin
offers attach to a separate EDEKA store, giving a third chain to compare per product
(e.g. avocado across Lidl/REWE/EDEKA). Same no-regular-price caveat as REWE.

**Categorization.** [`categories.py`](backend/app/categories.py) classifies each
offer with a path-aware, deterministic pipeline:

1. **Source taxonomy** — for flyer offers, Bonial's structured `categoryPaths`:
   a non-food level-1 node → "Household & Non-food"; otherwise the most specific
   product node (`…> Käse > Weichkäse` → cheese). This handles the bulk of the
   diverse flyer catalog.
2. **Brand map → override tokens → German-keyword rules** — for coupons and
   brand-only flyer food (a flavour word like "Mango"/"Pfirsich" can't beat the
   real category; substring traps like "li**mett**e" are space-guarded).

Reviewing all offers cut **"Other" from ~190 to ~2 of 482**. Categories are
computed at scrape time and stored (with the path), so after tuning, the backfill
— `python -m app.scripts.recategorize` (or `POST /api/recategorize`) — re-applies
them without re-scraping. The app **hides non-food by default** with a
"+ Non-food" toggle. Guards live in
[`tests/test_categories.py`](backend/tests/test_categories.py) (`pytest`).

## CI/CD (GitHub Actions)

Three workflows under [`.github/workflows/`](.github/workflows/):

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `ci.yml` | push / PR to `main` | Backend `ruff` + `pytest`, mobile ESLint + `tsc`, and a backend Docker image build. On green pushes to `main` it triggers the Render deploy. |
| `eas-update.yml` | push to `main` (`mobile/**`) + manual | Publishes an EAS Update (OTA) to the `production` channel. |
| `scrape.yml` | weekly cron + manual | POSTs to `/api/scrape` to refresh deals. |

Least-privilege permissions, dependency caching, and concurrency cancellation
throughout. CI is hermetic (tests use JSON fixtures — no network or secrets).

### One-time setup (to activate deploy + OTA)

The deploy and EAS Update steps **skip gracefully** until their secrets exist, so CI
is green out of the box. To turn them on:

**Gated Render deploy** (deploy only when CI is green):
1. Render dashboard → service → **Settings → turn OFF Auto-Deploy** (else it deploys
   on every push, bypassing the gate).
2. Settings → **Deploy Hook** → copy the URL.
3. GitHub repo → Settings → Secrets and variables → Actions → add
   **`RENDER_DEPLOY_HOOK_URL`**.

**EAS Update (OTA):**
1. expo.dev → Account → **Access Tokens** → create one.
2. Add it as the GitHub secret **`EXPO_TOKEN`**.
3. Run a fresh `eas build -p ios --profile production` once — OTA only reaches a build
   that embeds `expo-updates` at the matching runtime version, so the current
   TestFlight build won't receive updates until rebuilt.

**Branch protection (optional):** require the `Backend` and `Mobile` checks on PRs
(Settings → Branches).

## Roadmap

- [x] Backend pipeline: scrape → normalize → categorize → discount % → store
- [x] API: offers, categories, stores, basket optimizer
- [x] Live Lidl scraper (Lidl Plus store + offers endpoints; PLZ → nearest store)
- [x] Weekly Aktionsprospekt via Bonial/meinprospekt — ~430 structured flyer
      offers alongside the coupons, each tagged `coupon`/`flyer` in the app
- [x] React Native app: live deals by category, ranked by % off, with per-offer
      flyer images + tap-to-view (links to Lidl's full weekly Prospekt)
- [x] Set your postal code in-app — resolves the nearest Lidl and persists it
- [x] In-app search bar + Coupon/Prospekt source badges
- [x] REWE as a second chain (meinprospekt "Dein Markt" flyer, publisher
      `DE-1062`), with a per-offer store badge (Lidl/REWE) in the app
- [x] EDEKA as a third chain (meinprospekt flyer, publisher `DE-220164`) — ~300
      Berlin offers, an Edeka badge, and three-way per-product price comparison
- [x] Nearby-stores directory ("Stores"): nearest Lidl/REWE/Edeka/Aldi/Netto/
      Penny/Kaufland with addresses (OpenStreetMap), add non-active chains to a
      saved "My stores" list — groundwork for onboarding more chains; a "Change"
      picker lists every branch of a chain near the PLZ so you can pick the one
      actually near you (not just nearest the PLZ centroid)
- [x] Per-unit price (€/kg, €/l) shown on every offer that has one, plus REWE
      loyalty-card bonus badges ("1,00 € Bonus") — both pulled from data we
      already fetched but had been discarding
- [x] EDEKA app-coupon prices — a yellow "App 2,99 €" badge surfacing the
      app-exclusive price (`SPECIAL_PRICE` + "App-Preis"), ~24 EDEKA offers/PLZ
- [x] "Cheapest €/kg" sort — ranks the current view by normalized per-unit price
      (e.g. find the best-value beef per kg, independent of pack size)
- [x] Group similar products inside a category — pick Fruits/Beef/etc. and offers
      cluster by product (Avocado, Pfirsich, …) under a header so competing prices
      sit together (e.g. Avocado: REWE 0,88 € vs Lidl 1,99 €)
- [x] Filter by store (All / Lidl / REWE / EDEKA) — a session lens that narrows the
      whole list (and search) to one chain, with the brand colour on the active pill
- [x] **Basket** — a shopping list you build from common items (bilingual quick-add:
      type "Strawberry" or "Erdbeere"); each item shows its cheapest current deal plus
      a store-by-store shopping plan with the savings vs. one store (matched
      per-product against the live deals, client-side)
- [x] CI/CD pipeline (GitHub Actions) — test / lint / typecheck / Docker-build gates,
      gated Render deploy (deploy hook), EAS Update OTA, and a weekly scrape cron
- [x] Offline deals cache — instant open from an on-device cache + stale-while-revalidate
      refresh (no cold-start spinner; works offline), with a weekly-expiry "may be
      expired" banner and a "Deals as of <time>" stamp
- [x] Category-accuracy pass — mine more of the Bonial `categoryPaths` taxonomy + a
      product-image audit (uncategorized "Other" 11% → 1%; Fruits confirmed against images)
- [x] In-app OTA update prompt — alerts "Reload to update?" when an EAS Update is ready
- [ ] Production monitoring/alerting (uptime + scraper health) on a persistent DB
- [ ] Recipes from on-sale + pantry items (later phase)

## Legal

For personal use. Scrapers run at low frequency (weekly) with aggressive caching
and respect each site's terms of service.
