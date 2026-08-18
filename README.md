# Grocery Helper

Find the best weekly deals near you in Berlin. The app scrapes the weekly offers
("Angebote") from local supermarket **and drugstore** chains, normalizes and
categorizes them, computes the **% discount** for every item, and helps you
build the cheapest basket across one or two stores.

> **Status:** v1.1 in progress. The app opens on a home screen with **three sections —
> Grocery, Drinks and Drugstore** — and everything below it is scoped to one of them.
> **Live Lidl + REWE + EDEKA + E center + ALDI (grocery) and Rossmann + dm (drugstore)
> offers** + API + the React Native app work end-to-end — real Berlin prices,
> resolved from your postal code via the Lidl Plus endpoints, the meinprospekt
> weekly-flyer feed and dm's clearance API. Eight chains make the basket optimizer, the
> per-product grouping, and the **Compare Stores** face-off meaningful. The **backend is deployed on
> Render** (HTTPS), and the iOS app ships via **EAS → TestFlight** (build 1.1.0)
> with OTA updates.
> See [Deploy](#deploy-to-render-free-https-for-testflight) and [Roadmap](#roadmap).

## Highlights

- **Three shopping sections behind one home screen** — Grocery (six supermarket chains),
  Drinks (soft drinks, beer, wine and spirits from those same six) and Drugstore
  (Rossmann + dm), picked from three large buttons on launch. Every fetch, cache and
  filter chip is scoped to the chosen section, which is also what keeps each one clear of
  the API's 2,000-offer ceiling: as a single query all eight chains would be silently
  truncated, and grocery **alone** had reached 1,926 of 2,000 before Drinks was split out
  of it (now 1,689 + 237 + 495). Drinks shows the second shape a section can take — the
  first two are chain sets, it is a *category* carve-out over the grocery chains, so the
  two are one partition that a single frozen set defines for both. Each section keeps its
  own cached flyer week, so switching between them is instant and makes no network call
  at all.
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
  Tap any on-sale ingredient to open that deal's flyer without losing your place in the recipe.
  **"Shop at" scopes the whole screen to one store, or a mix of two**, so you only see meals you
  can actually buy on one trip — each card badges how many shops it takes. Recipes are authored
  **per chain** for exactly that reason: built from the cheapest item in each category regardless
  of store, a recipe's ingredients end up in four different shops by construction (measured: only
  3 of 10 were shoppable at the best single store; now every chain has 3–5).
  Customizable by diet, cuisine, servings, on-sale-only, and cheapest-€/kg. **Regenerated
  weekly by a scheduled local job** (launchd → headless Claude Code → validate → push → OTA),
  so the loop stays automatic *and* keyless (no managed API key anywhere).
- **Cross-platform client (iOS + web, one codebase)** — a React Native (Expo)
  app consuming the API to browse local deals by category, sorted by savings;
  the same code runs in the browser via Expo Web / react-native-web
  (`npm run web`).
- **Every category is sub-categorized** — inside a chip the deals list is grouped by the
  actual product, with a header per sub-group showing how many offers it holds and the
  cheapest price in it: Alcoholic splits into Bier · Wein · Sekt · Whisky · Gin · Likör,
  Pantry into Sauce · Nudeln · Reis · Speiseöl · Müsli · Konserven, and so on across all
  35 categories. Ice cream and coffee group by *form* rather than product (a stick, a tub
  and a multipack of cones are not substitutes); the Vegan chip groups by the food each
  product replaces. **82% of served offers carry a sub-group**, up from 39% — which also
  means they can be added to the basket by name.
- **Compare Stores price face-off** — pick stores and a category, and every product
  sub-group (Avocado, Butter, Milch…) lines up each store's cheapest price side by
  side with the winner highlighted — powered by a cross-source product-grouping
  taxonomy shared with the basket matcher.
- **Category browser** — a header button opens every category as a card showing its
  three most-discounted deals; tap one to jump straight into that category. Toggle
  between your categories and all of them, and edit your picks from a settings button
  in the same view. Categories that have fewer than three discounted items top the card
  up with their best value-per-kilo deals rather than showing gaps.
- **"My Categories" home** — pick the categories you actually shop and land on a
  personalized home of just those, each a preview shelf (its best deals + "See all"
  that opens the full category). The default "All" view is kept; a fresh install lands
  on All until you pick some. Each shelf sorts by its category's own best axis (€/kg
  for food), and the whole home reuses the same filtering pipeline as the list, so it
  never drifts from what the list would show.
- **Swipe-to-basket gesture** — swipe any deal left to add its product *category*
  to the shopping basket (a melon offer adds "Melon", which then tracks the cheapest
  melon all week) — native gesture handling with haptic feedback, and a resolver
  that reconciles the server's product sub-groups with the client catalog.
- **Shopping history with brand-aware re-matching** — everything you add to your
  basket is recorded with the price you paid, and the History page re-checks it
  against every new flyer week (a header badge shows how many are on sale again right
  now). Products are tracked by identity, not by id: if the flyer renames "McCain
  Golden Longs" to "Golden Long" next week, the exact match falls back to the brand's
  other offers (and to the product sub-group for brandless produce), ranked by name
  similarity. It's append-only — clearing your basket doesn't erase what you shopped for.
- **Price history that admits what it doesn't know** — each History row also shows the
  product's weekly price series, collected since July by a sibling project. Because 94%
  of tracked products have been seen in only one week so far, the row is tiered by
  evidence: nothing at all when there's no history (rather than a "no data" placeholder
  on almost every row), a single sighting when that's all there is, a price delta at two
  weeks, and only at three or more the full low/usual figures with a sparkline. It also
  refuses to state confident numbers when the underlying series mixes pack sizes — a
  "Coca-Cola" whose weekly prices span a can and a crate says so instead of averaging them.
- **At-a-glance basket marker on each deal** — a small cart in the card's tag row
  shows when a product is already in your basket, so you don't have to open the flyer
  to check. It updates live as you add (a memoization-safe wiring that keeps the swipe
  gestures smooth) and reads out as part of the card's spoken label, so a screen-reader
  user gets the same information.
- **Hide a deal you're not interested in** — swipe a deal right (or use the deal detail's
  Hide button) and it disappears from the list (and from the Basket, Recipes and Compare
  pages) for that flyer week, at that chain: hiding Edeka's Schnaps leaves Lidl's alone, and it returns when the
  flyers refresh. Hides are stored by product identity rather than by offer id, which
  churns on every re-scrape. Filters → "Show hidden" reveals them again to un-hide.
- **Persisted store visibility** — hide chains you never shop at; the preference
  survives restarts and applies everywhere prices are suggested (deals list, basket
  optimizer, recipe pricing), with a guard so the last visible store can't be hidden.
- **Modern, decluttered mobile UI** — secondary filters (store, sort, special-days,
  Bio, non-food) consolidated into a single bottom-sheet behind an active-filter chip
  bar, an icon-led header (`@expo/vector-icons`), and a small design-token system
  (spacing/type/radius/tint) replacing per-component hardcodes — plus a per-offer
  **"View payload"** inspector that shows the raw source data behind any deal.
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
  control, and **Dependabot raising pull requests for security advisories only** — routine
  version bumps are switched off, so a dependency PR always means there is a CVE.
- **Automated test suite** — ~1,507 backend tests (pytest) covering the scrapers,
  classifier, dedup, unit-price/validity logic, and HTTP-level API behavior
  (filters, auth guards, throttling), plus a React Native **Jest** suite (~450 tests)
  for the app's pure business logic (basket matching, the deals filter pipeline,
  recipe filtering, store comparison, catalog trap-guards); a model-vs-migration
  **drift check** (`alembic check`) fails CI if the ORM and schema diverge.
- **Multi-retailer ingestion across heterogeneous sources** — a single
  publisher-parameterized engine normalizes six German chains (Lidl, REWE, EDEKA, Penny,
  E center, ALDI) from two feed types (a private mobile coupon API and structured
  weekly-flyer data) into one schema, tagged by chain/source, powering a cross-store
  basket optimizer.
- **Geospatial store discovery** — an OpenStreetMap Overpass integration that
  finds the nearest branch of each major chain around a postal code (haversine
  ranking, multi-mirror failover, response caching), powering an in-app
  "nearby stores" directory with a saved-stores list.
- **Resilient scraping design** — store-agnostic normalization layer and
  fall-back data paths so a single upstream change never takes the app down.
- **In-app maintenance/admin controls** — an Options panel exposing client- and
  server-side data-lifecycle actions (clear on-device cache, full app reset,
  on-demand re-scrape, and a database wipe-and-reseed via `POST /api/reset`) —
  giving an operator one-tap recovery from stale cache or bad data without a redeploy.
- **Hardened public API surface** — destructive endpoints require an `ADMIN_TOKEN`
  sent as an `X-Admin-Token` header (timing-safe comparison, failed attempts logged
  with the client host), and the on-demand scrape is throttled (per-PLZ cooldown +
  global rate limit) so third parties can't hammer the upstream flyer sites through
  the server — while the app's cold-start scrape path stays unblocked.
- **Day-aware deal validity** — parses each offer's true on-sale window from a
  per-record validity field the feed buries (timezone-correct via `zoneinfo`), so
  day-limited specials (e.g. weekend-only deals) are badged with their days and
  filterable as "special days", and ended specials expire correctly instead of
  lingering for the whole flyer week.
- **Organic ("Bio") product filter** — deterministically flags organic offers from the
  German name/brand (word-boundary "Bio"/"Öko"/"Organic" + organic certifiers like
  Bioland/Demeter, trap-guarded against mid-word matches), computed at serve time with no
  schema change — surfaced as a one-tap "Bio only" filter with a green badge on each organic deal.
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
| GET    | `/api/offers`     | Offers; filter by `vertical` (`grocery\|drinks\|drugstore` — omitted means grocery; an unknown value 422s), `category`/`chain`/`plz`/`min_discount`, `sort=discount\|price` |
| GET    | `/api/categories` | Categories that currently have offers, w/ counts; takes the same `vertical` scope as `/api/offers`, so the chips always describe the list they filter |
| GET    | `/api/offers/{id}/payload` | The full raw source payload an offer was scraped from (for the app's "View payload") |
| GET    | `/api/stores`     | Known stores                                     |
| GET    | `/api/nearby-stores` | Nearest branch of each major chain near a PLZ (OSM); `active` flag for chains we scrape |
| POST   | `/api/optimize`   | Cheapest basket across 1–2 stores                |
| POST   | `/api/scrape`     | Re-run scrapers on demand (throttled: per-PLZ cooldown + global rate limit) |
| POST   | `/api/recategorize` | Re-apply the classifier to stored offers (requires `X-Admin-Token` when `ADMIN_TOKEN` is set) |
| POST   | `/api/reset`      | Wipe all offers + re-scrape (weekly refresh; requires `X-Admin-Token` when `ADMIN_TOKEN` is set) |
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

**E center weekly flyer** (`source="flyer"`, `chain="edeka_center"`) — EDEKA's
hypermarket format has its **own** meinprospekt publisher (`DE-3443181`), so it's
scraped as a fourth, separate chain (~290 offers/PLZ) — which is what makes the
EDEKA-vs-E-center face-off in **Compare Stores** possible. Because the two flyers
overlap heavily (measured: 103 of E center's 272 products are also at EDEKA, **98% at an
identical price**), the deals list hides the E center copies that merely repeat EDEKA —
unless E center is **cheaper**, since a lower price isn't a duplicate. All copies are
kept in the data, so Compare and the EDEKA-vs-E-center page still show the full overlap.

**ALDI weekly flyer** (`source="flyer"`, `chain="aldi"`) — ALDI is two independent
companies with disjoint territories (ALDI Nord `DE-75`, ALDI SÜD `DE-77`), and **both**
meinprospekt publishers are national: each serves the identical brochure to Berlin and
Munich, so the feed will not say which one is actually yours. The scraper picks the
division that operates at the postal code from OpenStreetMap's per-branch tags, and
scrapes only that one — if it can't tell, ALDI is skipped and logged rather than guessed,
because a missing chain is visible whereas wrong-region deals are not (~244 offers/PLZ).

**Rossmann weekly flyer** (`source="flyer"`, `chain="rossmann"`) — the drugstore section's
chain, and the same engine again for publisher `DE-1064` (~280 offers/PLZ). It publishes a
weekly "Mein Drogeriemarkt" alongside a months-long campaign brochure; the engine's
flyer-length rule keeps the weekly one.

**dm clearance** (`source="clearance"`, `chain="dm"`,
[`dm.py`](backend/app/scrapers/dm.py)) — the drugstore section's second chain, and the
only source that isn't a flyer or a coupon. dm's meinprospekt brochure serves an empty
page, so no flyer offer can ever be parsed from it; instead this reads the **Ausverkauf
(clearance) facet of dm's product-search API** — the whole feed in a single request
(~250 products, ~215 of them stocked in a branch). It is the app's best-quality discount
source: **every item carries a struck-through original price** (median 48% off), plus an
image and a category. Three things the parser is careful about, each pinned by a test:
the API also returns a `netPrice` that is *net of VAT* and must never be used as the
price; the Grundpreis string leads with the pack size rather than the unit price
(`"0,036 kg (81,94 € je 1 kg)"`); and "Nur Online" items are skipped because they aren't
stocked in a branch. Prices are national, so unlike the flyer scrapers this one needs no
postal-code coordinates — and it deliberately runs *before* the coordinate lookup, so a
Lidl outage can't take dm down with it.

**Categorization.** [`categories.py`](backend/app/categories.py) classifies each
offer with a path-aware, deterministic pipeline:

1. **Source taxonomy** — for flyer offers, Bonial's structured `categoryPaths`:
   a non-food level-1 node → "Household & Non-food"; otherwise the most specific
   product node (`…> Käse > Weichkäse` → cheese). This handles the bulk of the
   diverse flyer catalog.
2. **Flyer caption → brand map → override tokens → German-keyword rules** — the
   product name is marketing copy that lies (a flavour word steals the item), so
   the supplier's own caption is read as a second signal, then unambiguous brands,
   then keyword rules. Substring traps ("li**mett**e", Milk**ana**, In**sekt**enabwehr)
   are space-guarded, and a keyword that only fires by coincidence is pinned to the
   product that proved it.

The taxonomy spans **20+ categories** (including Lamb & Other Meat, Eggs, Ready
Meals, and a cross-cutting Vegan section). A CI **self-disagreement gate** flags any
product name served under two categories — free to compute and needing no ground
truth, since a classifier contradicting itself is wrong by construction.

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
| `eas-update.yml` | after a green CI run on `main` + manual | Publishes an EAS Update (OTA) to the `production` channel — gated on a successful CI run (via `workflow_run`), and only when `mobile/**` changed, so a failing build can't reach users. |
| `scrape.yml` | Sunday cron + manual | Wipes & re-scrapes via `POST /api/reset` (flyers are weekly, spent by Sunday) — retries 3× and opens/comments a self-alerting failure issue. A `verify_only` dispatch input re-checks the deployed data **without** wiping it, so a mid-week fix can clear a stale alert. |

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

**Branch protection:** `main` is governed by two GitHub rulesets — *protect history*
(no force-push, no deletion) and *require green PR* (required `Backend` / `Mobile` /
Docker-build checks, squash-only, linear history) with a scoped admin bypass so
zero-risk docs can still be pushed directly.

## Experience Gained

Engineering practices demonstrated while building and operating this project:

- **Designing a regression gate that can tell a refinement from a defect** — A
  before/after diff over 17,000 records reported 48 "regressions" while a classification
  taxonomy was being deliberately refined; reading the moved rows showed 46 were exactly
  the intended outcome (a generic bucket resolving into a specific one) and only 3 were
  real. Re-cut the comparison into three transition classes — newly classified,
  generic-to-specific, and genuinely wrong — so the gate reports a number that means
  something. A binary "did anything change" verdict is correct only while a change is
  purely additive, and silently useless the moment it is meant to reclassify.
- **Break-test-restore verification of a rule engine** — Built a harness that mutates a
  production rules table one guard at a time and asserts the corresponding test fails,
  guarding every way such a harness lies: a mutation that never applied, a compiled-bytecode
  cache serving the pre-mutation module, and a shrinking test count masquerading as passes.
  It caught two tests that were passing for the wrong reason — one whose fixture an earlier
  rule already claimed, so it never exercised the rule it was named after.
- **Extending a production ingestion pipeline to a new upstream source** — Added a sixth
  retailer by measuring first: probed three candidates' feeds, quantified parse quality
  (image, taxonomy, unit-price and discount coverage) against the existing gate's
  thresholds, and chose on a capacity constraint the naive answer would have missed — the
  API truncates after a relevance sort, so an oversized source would have silently dropped
  the very records the product compares. Zero parser changes were needed; the rejected
  candidates and the reasoning are recorded as an architecture decision record.
- **Fail-closed data integrity** — Found that a failed supplier import silently published
  *fabricated* records: placeholder prices with plausible validity windows, indistinguishable
  downstream from real ones and about to be recorded as a week's genuine pricing by a separate
  history collector. Traced the root cause to an exception handler that logged nothing at all —
  the diagnostic sat outside the `except` block, so the runtime had already discarded the error
  — and rewrote the degradation to serve nothing, surface the failure on a metrics endpoint, and
  keep the placeholder data for local development behind a flag defaulted off so production is
  correct with no configuration.
- **Data-quality auditing at scale** — Audited a 2,700-product taxonomy by rendering
  every item's photograph into per-category contact sheets and judging each against its
  source caption, rather than trusting the product name. This surfaced a systematic
  defect the names concealed: a marketing string routinely misidentifies a product
  ("Bauer Diplomat Paprika" is a cheese), while the supplier's own caption states the
  legal designation — data already captured and never used. Feeding it into the
  classifier reclassified 107 records with zero regressions, verified by a full-dataset
  old-versus-new diff and confirmed against the live API.
- **A ground-truth-free correctness gate in CI** — Added an automated check that flags any
  product name served under two different categories: a classifier contradicting itself is
  wrong by construction, so the signal needs no labelled dataset. Getting the denominator
  right was the crux — the served set is deduplicated, so measuring against the total made
  the rate look tiny and the gate near-inert; scoping it to comparable products (names that
  appear more than once) and proving it both ways (passes on live data, fails on a
  category-scrambled fixture, skips when there is nothing to compare) turned it into a real
  smoke alarm for taxonomy drift.
- **Shipping a personalized home without a parallel data path** — Added a "pick your
  categories" landing view by composing the existing filter pipeline rather than forking it:
  the personalized sections are derived from the same pure function that builds the list, so
  the two can never disagree on price, filtering, or sort. Modelled the preference on the
  project's established persisted-preference pattern (empty set falls back to the default view,
  so a first-run screen is never blank), kept the entry points inside a width-constrained header
  by reusing the existing chip row, and covered the new behavior with unit tests for the pure
  builder plus component tests that prove the default-landing rule and the drill-in both ways.
- **Root-causing a platform-specific defect on the real platform** — Diagnosed a bug
  that browser testing could not observe by construction, by reproducing it on a device
  simulator against the platform's own console: the framework refuses a UI presentation
  when two views share a parent, then records success anyway, so a single failure
  disabled the feature for the remainder of the session. Located the mechanism in the
  vendored framework source, corrected two pieces of documentation the evidence
  disproved, and pinned the constraint with a regression test.
- **Correctness engineering against an unreliable upstream** — Established that a
  third-party feed served *nationally scoped* data while presenting it as local, which
  would have shown users deals from retailers ~300 km away. Proved it by differential
  probing (same query from two locations, against a known-regional control), then built
  geospatial routing from an independent data source to select the correct regional
  operator — designed to fail closed and emit a warning when it can't decide, on the
  principle that a missing data source is visible while wrong data is not.
- **Property-based testing & test-gate engineering** — Introduced Hypothesis property
  tests over the feed parsers (run deterministically in CI, exploratory locally) that
  uncovered four latent defects in one pass, including a single-malformed-element failure
  mode that degraded a whole retailer to sample data; hardened the parse path to be total
  over arbitrary JSON and proved the change behavior-identical across all 5,800+ stored
  real payloads. Corrected a misleading coverage setup (only-imported-files reporting 81%
  vs. a true 64%) and pinned both stacks under ratcheting coverage floors in CI.
- **Self-verifying continuous deployment** — Deploys no longer trust the trigger: the
  health endpoint exposes the running commit, and the pipeline polls production until the
  merged SHA is live (failing closed when the platform build never swaps), then asserts
  the service serves real data. A scheduled data-quality gate checks retailer coverage and
  parse-rate floors weekly, feeding an auto-opening, auto-closing incident issue workflow.
- **Polite, resilient outbound scraping** — Made the data collector a well-behaved client
  of the third-party sites it depends on. Centralized every outbound call through a custom
  HTTP transport that paces requests (a global minimum gap + jitter) so a scrape no longer
  hits the flyer aggregators as one detectable burst, and retries transient rate-limit/5xx
  responses with `Retry-After`-aware exponential backoff — capped so an unattended weekly job
  can't hang, and never retrying a hard block. Made throttling observable (a 429 was previously
  indistinguishable from a parse failure that silently served sample data) by metering it into
  the outbound-call dashboard. Bounded a request-amplification vector by rate-limiting the
  public endpoint that fans out to a free geocoding service, protecting the server's standing
  with that upstream.
- **CI/CD pipeline design & hardening** — Built a multi-job GitHub Actions pipeline
  (lint, tests + coverage, Docker image build) that gates an automated Render
  deployment and an Expo over-the-air release. Closed an unguarded release path by
  gating the OTA publish on a successful CI run via `workflow_run`, so failing builds
  can't reach users.
- **Repository governance as code** — Codified branch protection with GitHub rulesets
  (immutable history + required status checks with a scoped admin bypass), provisioned
  through the REST API rather than the dashboard.
- **Infrastructure as Code & containerization** — Dockerized FastAPI backend deployed
  from a version-controlled `render.yaml` Blueprint, with Docker Compose + PostgreSQL
  for local/production parity.
- **Database migration management** — Alembic-managed schema with auto-upgrade on
  startup, SQLite/PostgreSQL parity, and a CI drift check.
- **Scheduled automation & observability** — Cron-driven weekly data refresh with
  retry logic and self-alerting failure issues, plus outbound-API call metrics
  surfaced on a live dashboard.
- **Keyless AI automation** — A weekly content-generation pipeline that runs a headless
  LLM step under local auth (macOS launchd → `claude -p`), gated on a typecheck/lint build
  check before it commits and ships over-the-air — no managed API key anywhere, in CI or at runtime.
- **Dependency & supply-chain management** — Dependabot reduced to security advisories only,
  so a dependency pull request always signals a CVE rather than routine churn; this also
  avoids framework-lockstep breakage in an Expo SDK-pinned app, where per-package bumps break
  the install. All GitHub Actions pinned to commit SHAs and release-tooling versions pinned,
  so no third-party tag move can alter the pipeline.
- **API security hardening** — Token-guarded destructive endpoints (header-based,
  timing-safe comparison, audit-logged failures), abuse throttling on the public
  scrape trigger, and a non-root container image — applied after a structured
  security review of the deployed surface.
- **Path-scoped deployment gating & client resilience** — Scoped the CI deploy job to fire
  only when a merge changes backend code (a `git diff` path filter), so mobile-only and docs
  merges don't needlessly redeploy — and wipe the ephemeral free-tier database of — the
  backend. Paired with client-side cold-start resilience: automatic retry with back-off that
  distinguishes retryable failures (timeouts, network errors, 5xx) from real client errors
  (4xx), so a sleeping or redeploying backend self-recovers instead of surfacing an error.
- **Data-quality engineering against a third-party feed** — Persisted every source payload, so
  "are we losing data?" became a measurable join (stored column × payload field) instead of
  spot-checking. Auditing all ~4,000 payloads turned single user-reported anomalies into
  quantified classes and recovered value the pipeline had been silently discarding: struck-through
  prices for **~21% of offers** (an entire unparsed deal type), and comparable €/kg coverage
  **53% → 72%** by normalizing the feed's inconsistent per-unit formats — parenthesized values an
  anchored regex rejected (which were also rendering as UI garbage), and labels standing in for
  values. Every fix shipped behind an old-vs-new diff over the full dataset proving zero
  regressions, with the parser rules locked in by unit tests.
- **Runtime/toolchain drift detection** — Caught that dependency floors had advanced past the
  documented dev interpreter while a long-lived virtualenv masked it (only a *fresh* install fails).
  Migrated dev onto the same Python as CI and the production image, verified with a dry-run resolve
  before committing and by a from-scratch CI build.

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
      per-product against the live deals, client-side). The plan **lists each item under
      its store** with the product you'd actually pick up, so it reads as a shopping list —
      and it **follows the "Only show" store lens**: narrow the deals to Lidl and Aldi and
      the plan is built from those two, while what you can *add* stays the full week.
      An **"In this week's flyers"**
      section lists every product sub-category actually on offer — grouped by aisle, so
      Kohlrabi or Pfifferling can be added even though no curated catalogue lists them.
      Adding from there and swiping a deal card produce the same basket entry
- [x] CI/CD pipeline (GitHub Actions) — test / lint / typecheck / Docker-build gates,
      gated Render deploy (deploy hook), EAS Update OTA, and a weekly scrape cron
- [x] Offline deals cache — instant open from an on-device cache + stale-while-revalidate
      refresh (no cold-start spinner; works offline), with a weekly-expiry "may be
      expired" banner and a "Deals as of <time>" stamp
- [x] Category-accuracy pass — mine more of the Bonial `categoryPaths` taxonomy + a
      product-image audit (uncategorized "Other" 11% → 1%; Fruits confirmed against images)
- [x] In-app OTA update prompt — alerts "Reload to update?" when an EAS Update is ready
- [x] Hide/show stores — persisted multi-select store visibility, applied to the deals
      list, basket optimizer, and recipe pricing alike
- [x] Swipe-to-basket — swipe a deal left to add its product sub-category (the same
      entry the basket's "+" adds), with haptic feedback (native build 1.1.0)
- [x] E center as a fourth chain (own meinprospekt publisher `DE-3443181`) — EDEKA's
      hypermarket flyer as a separate store
- [x] Compare Stores — a per-product price face-off across selected stores, cheapest
      highlighted, tap-through to the deal
- [x] Security & ops hardening — header-based admin auth on destructive endpoints,
      scrape throttling, Berlin-timezone validity, supply-chain-pinned CI, non-root
      container
- [x] Grocery / Drugstore sections — a home screen with large buttons, with every
      fetch, cache and chip scoped to the chosen one (which is also what keeps each
      section clear of the API's 2,000-offer ceiling)
- [x] Drinks as a third section — soft drinks, beer, wine and spirits out of the food
      list, carved from the grocery chains by *category* rather than by chain, which
      also took grocery from 1,926 of the 2,000-offer cap down to 1,689
- [x] Rossmann as the drugstore chain, plus 11 drugstore categories (hair, face, body,
      dental, fragrance, baby, health, cleaning, laundry, pet, make-up) so its offers
      stop collapsing into "Household & Non-food"
- [x] dm as the second drugstore chain — sourced from its **Ausverkauf (clearance) API**
      rather than a flyer, since its meinprospekt brochure serves no offers. Every item
      carries a struck-through original price (median 48% off), the best discount
      coverage of any chain in the app
- [ ] dm's full catalog (~21k products at everyday prices, no validity window) — still a
      different data model from the deals pipeline; likely belongs in the price-history
      collector rather than here
- [x] Weekly price history on History rows, read from the companion
      `grocery-price-history` collector and tiered by how much evidence exists
- [ ] Production monitoring/alerting (uptime + scraper health) on a persistent DB
- [ ] "Store scorecard" compare view — per-store summary (deal count, avg discount,
      which categories each store wins)

## Legal

For personal use. Scrapers run at low frequency (weekly) with aggressive caching
and respect each site's terms of service.
