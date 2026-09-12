# Grocery Helper

Find the best weekly deals near you in Berlin. The app scrapes the weekly offers
("Angebote") from local supermarket **and drugstore** chains. It tidies them up, sorts
them into categories, works out the **% discount** on every item, and helps you build
the cheapest basket across one or two stores.

> **Status:** v1.1 in progress. The app opens on a home screen with **three sections —
> Grocery, Drinks and Drugstore** — and everything below it belongs to one of them.
> **Live Lidl + REWE + EDEKA + E center + ALDI (grocery) and Rossmann + dm (drugstore)
> offers**, the API and the React Native app all work end to end. The prices are real
> Berlin prices, resolved from your postal code through the Lidl Plus endpoints, the
> meinprospekt weekly-flyer feed and dm's clearance API. Eight chains are what make the
> basket optimizer, the per-product grouping and the **Compare Stores** face-off worth
> having. The **backend runs on Render** (HTTPS), and the iOS app ships through
> **EAS → TestFlight** (build 1.1.0) with OTA updates — new code delivered straight to
> the phone, without an App Store release.
> See [Deploy](#deploy-to-render-free-https-for-testflight) and [Roadmap](#roadmap).

## Highlights

- **Three shopping sections behind one home screen** — Grocery (six supermarket chains),
  Drinks (soft drinks, beer, wine and spirits from those same six) and Drugstore
  (Rossmann + dm). You pick one from three large buttons when the app opens. Every fetch,
  cache and filter chip belongs to the section you chose. That is also what keeps each one
  clear of the API's 2,000-offer ceiling: as a single query, all eight chains would be cut
  off without warning, and grocery **alone** had reached 1,926 of 2,000 before Drinks was
  split out of it (now 1,689 + 237 + 495). Drinks shows the second shape a section can
  take. The first two are sets of chains; Drinks is a *category* carve-out over the grocery
  chains. So the two are one split, and a single frozen set defines both halves. Each
  section keeps its own cached flyer week, so switching between them is instant and makes
  no network call at all. Grocery and Drinks are the same six shops, so the **Basket,
  Recipes and History read both** — a beer belongs on the same list as the bread — while
  the deals list stays inside the section you are in.
- **Browse the actual paper flyer, page by page** — each store row opens the first pages
  of its weekly brochure as a swipeable, pinch-zoomable pager, because that is where the
  chains put their best deals. The page images cost **nothing extra to collect**: they were
  already inside the JSON each scrape fetches for the offers, and were being thrown away.
  The chains publish several brochures a week under identical titles and dates (REWE ran
  three at 34, 30 and 24 pages), so the biggest is served first — its size is the only
  thing that tells them apart. A chain with no captured flyer is simply missing from the
  response, and that absence is what hides the link. So a chain with no brochure at all
  needs no special case anywhere in the app.
- **Automated grocery-deal ETL pipeline** — a cron job (a task that runs on a timetable),
  running in a container, scrapes weekly offers from several German retail sources. It
  writes them into one relational database in a common shape, and works out each item's
  discount percentage.
- **Reverse-engineered a retailer's private mobile API** — it finds the nearest store from
  a postal code, then pulls live structured offer data (current + regular price) from
  Lidl's app endpoints. That yields exact discount percentages.
- **Discount-ranking & multi-store basket optimization API** — a FastAPI service with
  endpoints that filter offers by category, rank them by % discount, and work out the
  cheapest basket across one or two stores.
- **In-app shopping-list basket with cross-store price optimization** — you build a grocery
  list, and it takes either language ("Strawberry" or "Erdbeere"). The app matches each
  entry **per-product** against the live deal set, entirely on the device. It shows the
  cheapest offer per item and a store-by-store shopping plan, with the savings against
  shopping at a single store. Matching is plain keyword matching, so the same list always
  gives the same answer (no LLM), and it reuses the faceted dataset already loaded in
  memory, so results are instant.
- **Offline LLM-authored recipe generator (zero runtime API cost)** — an AI "Recipes"
  feature that suggests meals from the week's on-sale items plus the staples you say you
  always have. An LLM writes the recipes offline from the live deal database, and they
  reach devices **over-the-air**: no model call at runtime, no API key or secret, no server
  cost. The app renders them fully offline, and reuses the deterministic basket matcher to
  show each ingredient's real on-sale price and mark it as on sale, a pantry staple, or
  still to buy. Tap any on-sale ingredient to open that deal's flyer without losing your
  place in the recipe. **"Shop at" narrows the whole screen to one store, or a mix of two**,
  so you only see meals you can actually buy on one trip, and each card badges how many
  shops it takes. Recipes are written **per chain** for exactly that reason: built from the
  cheapest item in each category regardless of store, a recipe's ingredients end up in four
  different shops every time (measured: only 3 of 10 were shoppable at the best single
  store; now every chain has 3–5). You can set diet, cuisine, servings, on-sale-only and
  cheapest-€/kg. **A scheduled local job rebuilds them weekly** (launchd → headless Claude
  Code → validate → push → OTA), so the loop stays automatic *and* keyless — no managed API
  key anywhere.
- **Cross-platform client (iOS + web, one codebase)** — a React Native (Expo) app that
  reads the API to browse local deals by category, sorted by savings. The same code runs
  in the browser through Expo Web / react-native-web (`npm run web`).
- **Every category is sub-categorized** — inside a chip the deals list is grouped by the
  actual product, and each sub-group's header shows how many offers it holds and the
  cheapest price in it: Alcoholic splits into Bier · Wein · Sekt · Whisky · Gin · Likör,
  Pantry into Sauce · Nudeln · Reis · Speiseöl · Müsli · Konserven, and so on across all
  35 categories. Ice cream and coffee group by *form* rather than product, because a stick,
  a tub and a multipack of cones are not substitutes. The Vegan chip groups by the food
  each product stands in for. **82% of served offers carry a sub-group**, up from 39% —
  which also means you can add them to the basket by name.
- **Compare Stores price face-off** — pick stores and a category, and every product
  sub-group (Avocado, Butter, Milch…) lines up each store's cheapest price side by side,
  with the winner highlighted. It runs on the cross-source product-grouping taxonomy that
  the basket matcher also uses.
- **Category browser** — a header button opens every category as a card showing its three
  most-discounted deals; tap one to jump straight into that category. You can switch
  between your categories and all of them, and edit your picks from a settings button in
  the same view. A category with fewer than three discounted items tops its card up with
  its best value-per-kilo deals, rather than showing gaps.
- **"My Categories" home** — pick the categories you actually shop and land on a home page
  of just those. Each one is a preview shelf: its best deals plus "See all", which opens
  the full category. The default "All" view stays, and a fresh install lands on All until
  you pick some. Each shelf sorts by its category's own best axis (€/kg for food), and the
  whole home reuses the same filtering pipeline as the list, so it never drifts from what
  the list would show.
- **Swipe-to-basket gesture** — swipe any deal left to add its product *category* to the
  shopping basket. A melon offer adds "Melon", which then tracks the cheapest melon all
  week. It uses native gesture handling with haptic feedback, plus a resolver that lines
  the server's product sub-groups up with the client catalog.
- **Shopping history with brand-aware re-matching** — everything you add to your basket is
  recorded with the price you paid, and the History page re-checks it against every new
  flyer week. A header badge shows how many are on sale again right now. Products are
  tracked by identity, not by id: if the flyer renames "McCain Golden Longs" to "Golden
  Long" next week, the exact match falls back to the brand's other offers (and to the
  product sub-group for brandless produce), ranked by how close the names are. The list is
  append-only — clearing your basket doesn't erase what you shopped for.
- **Price history that admits what it doesn't know** — each History row also shows the
  product's weekly price series, collected since July by a sibling project. 94% of tracked
  products have been seen in only one week so far, so the row shows only as much as the
  evidence supports: nothing at all when there is no history (rather than a "no data"
  placeholder on almost every row), a single sighting when that is all there is, a price
  delta at two weeks, and only at three or more the full low/usual figures with a
  sparkline. It also refuses to state confident numbers when the underlying series mixes
  pack sizes — a "Coca-Cola" whose weekly prices span a can and a crate says so instead of
  averaging them.
- **At-a-glance basket marker on each deal** — a small cart in the card's tag row shows
  when a product is already in your basket, so you don't have to open the flyer to check.
  It updates live as you add (the wiring is memoization-safe, so the swipe gestures stay
  smooth), and it is read out as part of the card's spoken label, so a screen-reader user
  gets the same information.
- **Hide a deal you're not interested in** — swipe a deal right (or use the deal detail's
  Hide button) and it disappears from the list, and from the Basket, Recipes and Compare
  pages, for that flyer week at that chain. Hiding Edeka's Schnaps leaves Lidl's alone, and
  it comes back when the flyers refresh. Hides are stored by product identity rather than
  by offer id, which churns on every re-scrape. Filters → "Show hidden" reveals them again
  so you can un-hide.
- **Persisted store visibility** — hide chains you never shop at. The preference survives
  restarts and applies everywhere prices are suggested (deals list, basket optimizer,
  recipe pricing), with a guard so the last visible store can't be hidden.
- **Modern, decluttered mobile UI** — the secondary filters (store, sort, special-days,
  Bio, non-food) sit in a single bottom sheet behind a bar of active-filter chips. The
  header is icon-led (`@expo/vector-icons`), and a small design-token system
  (spacing/type/radius/tint) replaces per-component hardcodes. Every offer also has a
  **"View payload"** inspector that shows the raw source data behind the deal.
- **Containerized, deployable stack** — a Dockerized backend with Docker Compose +
  PostgreSQL, built for CI/CD deployment to a PaaS, with scraper health monitoring and
  alerting.
- **Versioned database migrations (Alembic)** — schema changes are tracked migrations,
  managed by Alembic, a tool that versions database changes. One config covers SQLite in
  dev and PostgreSQL in prod, and migrations run automatically at startup. This replaces
  ad-hoc table creation, so columns can evolve safely on a database that keeps its data;
  a legacy pre-migration database is auto-stamped rather than re-created.
- **CI/CD pipeline (GitHub Actions)** — every push and PR runs test, lint, type-check and
  Docker-build gates in parallel (backend `pytest` **with coverage reporting** + mobile
  **Jest**, ruff, ESLint, `tsc`). Production deploys to Render go out through deploy hooks,
  and only when the build is green. Mobile updates ship over the air through EAS Update. A
  scheduled weekly data-refresh cron **retries and opens a GitHub issue on failure**. The
  pipeline uses least-privilege permissions, dependency caching and concurrency control,
  and **Dependabot raises pull requests for security advisories only** — routine version
  bumps are switched off, so a dependency PR always means there is a CVE (a published
  security flaw).
- **Automated test suite** — ~1,630 backend tests (pytest) cover the scrapers, classifier,
  dedup, unit-price and validity logic, and HTTP-level API behavior (filters, auth guards,
  throttling). A React Native **Jest** suite (~475 tests) covers the app's pure business
  logic: basket matching, the deals filter pipeline, recipe filtering, store comparison and
  catalog trap-guards. A model-vs-migration **drift check** (`alembic check`) fails CI if
  the ORM and the schema no longer agree.
- **Multi-retailer ingestion across heterogeneous sources** — one publisher-parameterized
  engine brings six German chains (Lidl, REWE, EDEKA, Penny, E center, ALDI) into a single
  schema from two feed types: a private mobile coupon API and structured weekly-flyer data.
  Each record is tagged by chain and source, and the result powers a cross-store basket
  optimizer.
- **Geospatial store discovery** — an OpenStreetMap Overpass integration finds the nearest
  branch of each major chain around a postal code (haversine ranking, multi-mirror
  failover, response caching). It powers an in-app "nearby stores" directory with a
  saved-stores list.
- **Resilient scraping design** — a store-agnostic normalization layer and fall-back data
  paths, so a single upstream change never takes the app down.
- **In-app maintenance/admin controls** — an Options panel with data-lifecycle actions on
  both sides: clear the on-device cache, reset the app completely, re-scrape on demand, and
  wipe and reseed the database via `POST /api/reset`. An operator can recover from a stale
  cache or bad data with one tap, without a redeploy.
- **Hardened public API surface** — destructive endpoints need an `ADMIN_TOKEN`, sent as an
  `X-Admin-Token` header and compared in constant time, and failed attempts are logged with
  the client host. The on-demand scrape is throttled (per-PLZ cooldown + global rate limit),
  so third parties can't hammer the upstream flyer sites through the server — while the
  app's own cold-start scrape path stays open.
- **Day-aware deal validity** — the app reads each offer's true on-sale window from a
  per-record validity field the feed buries, with the right timezone via `zoneinfo`. So
  day-limited specials (weekend-only deals, say) are badged with their days and can be
  filtered as "special days", and specials that have ended expire correctly instead of
  lingering for the whole flyer week.
- **Organic ("Bio") product filter** — organic offers are flagged from the German name and
  brand, the same way every time: word-boundary "Bio"/"Öko"/"Organic" plus organic
  certifiers like Bioland and Demeter, trap-guarded so mid-word matches don't count. It is
  computed at serve time with no schema change, and surfaces as a one-tap "Bio only" filter
  with a green badge on each organic deal.
- **Outbound-call observability** — every request to an upstream site is instrumented
  (httpx event hooks) and tallied by source and host, alongside a timestamped log of the
  latest calls. It is exposed at `GET /api/scrape-stats` with a live `/stats` dashboard, so
  you can keep an eye on scrape volume and avoid tripping the sites' burst throttling.
- **Structured logging & error tracking** — structured logging to stdout, from the standard
  library, surfaces scraper and locator failures that used to be silent: a fall back to
  sample data is now logged, not hidden. Opt-in **Sentry** error tracking captures unhandled
  API exceptions when a DSN is configured, and does nothing when one isn't.

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

Local dev uses SQLite and seeds sample data on first start, so there is no database to
install.

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
Blueprint. It deploys [`backend/Dockerfile`](backend/Dockerfile) as a Render web service
with a free managed HTTPS URL (`https://<name>.onrender.com`). That URL is what the
iOS/TestFlight build talks to: a real device can't reach `localhost`, and iOS requires
HTTPS. Apply it in the Render dashboard → **New → Blueprint**, which reads `render.yaml`
from the repo. The container binds to Render's `$PORT`, and `/health` is the health check.
The mobile production build points at this URL via `EXPO_PUBLIC_API_URL` in
[`mobile/eas.json`](mobile/eas.json).

> Free-tier note: the instance sleeps after ~15 min idle and cold-starts on the next
> request. The app re-seeds by scraping on boot, so the first call after a sleep is slow.
> For data that lasts, attach a Render Postgres or a persistent disk and set
> `DATABASE_URL` (the app already supports Postgres — see `docker-compose.yml`).

### Build for iOS / TestFlight (EAS)

```bash
cd mobile
eas login                              # your Expo account
eas init                               # links the EAS project
eas build -p ios --profile production  # cloud build (first run sets up Apple signing)
eas submit -p ios --latest             # upload the .ipa to TestFlight
```

Config lives in [`mobile/eas.json`](mobile/eas.json), which auto-increments build numbers
remotely, and in `mobile/app.json` (`ios.bundleIdentifier`). Set `EXPO_PUBLIC_API_URL` in
`eas.json` to your deployed backend URL before you build.

## API

| Method | Path              | Purpose                                          |
| ------ | ----------------- | ------------------------------------------------ |
| GET    | `/api/offers`     | Offers; filter by `vertical` (`grocery\|drinks\|drugstore` — omitted means grocery; an unknown value 422s), `category`/`chain`/`plz`/`min_discount`, `sort=discount\|price` |
| GET    | `/api/categories` | Categories that currently have offers, w/ counts; takes the same `vertical` scope as `/api/offers`, so the chips always describe the list they filter |
| GET    | `/api/offers/{id}/payload` | The full raw source payload an offer was scraped from (for the app's "View payload") |
| GET    | `/api/flyer-pages` | This week's brochure page scans, `{chain: [url, …]}`, ordered biggest-brochure-first; a chain with no flyer is absent |
| GET    | `/api/stores`     | Known stores                                     |
| GET    | `/api/nearby-stores` | Nearest branch of each major chain near a PLZ (OSM); `active` flag for chains we scrape |
| POST   | `/api/optimize`   | Cheapest basket across 1–2 stores                |
| POST   | `/api/scrape`     | Re-run scrapers on demand (throttled: per-PLZ cooldown + global rate limit) |
| POST   | `/api/recategorize` | Re-apply the classifier to stored offers (requires `X-Admin-Token`; **denied on a deployed instance until `ADMIN_TOKEN` is set**) |
| POST   | `/api/reset`      | Wipe all offers + re-scrape (weekly refresh; requires `X-Admin-Token`; **denied on a deployed instance until `ADMIN_TOKEN` is set**) |
| GET    | `/api/scrape-stats` | Outbound calls to the scraped sites, by source/host (total + a timestamped recent-calls log); on-demand dashboard at `/stats` (Refresh button) |

## Scrapers

Two sources feed each Lidl store, tagged by `Offer.source`:

**Lidl Plus coupons** (`source="coupon"`) —
[`lidl.py`](backend/app/scrapers/lidl.py): finds the nearest store for a postal code
through the Lidl Plus store-autocomplete endpoint, then pulls that store's app coupons
from `offers.lidlplus.com` (clean prices + exact discounts; ~50 items). Endpoints adapted
from [EvickaStudio/lidl-discounts](https://github.com/EvickaStudio/lidl-discounts).

**Weekly Aktionsprospekt** (`source="flyer"`) —
[`bonial.py`](backend/app/scrapers/bonial.py): the full printed weekly leaflet, via
meinprospekt (a Bonial property). It finds Lidl's current brochure on the publisher page
(`__NEXT_DATA__`) using the store's coordinates, then pulls ~430 **structured** offers —
name, brand, `SALES_PRICE` + `REGULAR_PRICE` (→ exact %), image, validity. No OCR needed,
because the data already arrives structured. It runs weekly with backoff, because Bonial
soft-throttles bursts. Both feeds fall back to sample data so the app stays up.

**REWE weekly flyer** (`source="flyer"`, `chain="rewe"`) — the same
[`bonial.py`](backend/app/scrapers/bonial.py) engine, pointed at REWE's meinprospekt
publisher (`DE-1062`, "Dein Markt"). Reusing the structured flyer pipeline sidesteps REWE's
Cloudflare-gated app API (`mobile-api.rewe.de`) altogether. ~400 structured offers with
names, brands, images and `categoryPaths` attach to a separate REWE store, which gives the
optimizer a real second chain to compare. One caveat: REWE's flyer carries no
struck-through "old" price, so most REWE items show a price (and a per-unit price)
**without a % discount**. The optimizer ranks by absolute price, so this doesn't affect it.

**EDEKA weekly flyer** (`source="flyer"`, `chain="edeka"`) — the same engine again, for
EDEKA's national meinprospekt publisher (`DE-220164`). ~300 structured Berlin offers attach
to a separate EDEKA store, giving a third chain to compare per product (avocado across
Lidl/REWE/EDEKA, say). Same no-regular-price caveat as REWE.

**E center weekly flyer** (`source="flyer"`, `chain="edeka_center"`) — EDEKA's hypermarket
format has its **own** meinprospekt publisher (`DE-3443181`), so it is scraped as a fourth,
separate chain (~290 offers/PLZ). That is what makes the EDEKA-vs-E-center face-off in
**Compare Stores** possible. The two flyers overlap heavily (measured: 103 of E center's 272
products are also at EDEKA, **98% at an identical price**), so the deals list hides the
E center copies that merely repeat EDEKA — unless E center is **cheaper**, since a lower
price isn't a duplicate. All copies are kept in the data, so Compare and the
EDEKA-vs-E-center page still show the full overlap.

**ALDI weekly flyer** (`source="flyer"`, `chain="aldi"`) — ALDI is two independent companies
whose territories don't overlap (ALDI Nord `DE-75`, ALDI SÜD `DE-77`), and **both**
meinprospekt publishers are national: each serves the identical brochure to Berlin and
Munich, so the feed will not say which one is actually yours. The scraper reads
OpenStreetMap's per-branch tags to see which division operates at the postal code, and
scrapes only that one. If it can't tell, it skips ALDI and logs it rather than guessing,
because a missing chain is visible whereas wrong-region deals are not (~244 offers/PLZ).

**Rossmann weekly flyer** (`source="flyer"`, `chain="rossmann"`) — the drugstore section's
chain, and the same engine again for publisher `DE-1064` (~280 offers/PLZ). Rossmann
publishes a weekly "Mein Drogeriemarkt" alongside a months-long campaign brochure, and the
engine's flyer-length rule keeps the weekly one.

**dm clearance** (`source="clearance"`, `chain="dm"`,
[`dm.py`](backend/app/scrapers/dm.py)) — the drugstore section's second chain, and the only
source that is neither a flyer nor a coupon. dm's meinprospekt brochure serves an empty
page, so no flyer offer can ever be parsed from it. Instead this reads the **Ausverkauf
(clearance) facet of dm's product-search API** — the whole feed in a single request (~250
products, ~215 of them stocked in a branch). It is the app's best-quality discount source:
**every item carries a struck-through original price** (median 48% off), plus an image and
a category. The parser is careful about three things, each pinned by a test. The API also
returns a `netPrice` that is *net of VAT* and must never be used as the price. The
Grundpreis string leads with the pack size rather than the unit price
(`"0,036 kg (81,94 € je 1 kg)"`). And "Nur Online" items are skipped, because they aren't
stocked in a branch. Prices are national, so unlike the flyer scrapers this one needs no
postal-code coordinates — and it deliberately runs *before* the coordinate lookup, so a
Lidl outage can't take dm down with it.

**Categorization.** [`categories.py`](backend/app/categories.py) classifies each offer with
a path-aware pipeline that gives the same answer every time:

1. **Source taxonomy** — for flyer offers, Bonial's structured `categoryPaths`: a non-food
   level-1 node → "Household & Non-food"; otherwise the most specific product node
   (`…> Käse > Weichkäse` → cheese). This handles the bulk of the diverse flyer catalog.
2. **Flyer caption → brand map → override tokens → German-keyword rules** — the product
   name is marketing copy, and it lies: a flavour word steals the item. So the supplier's
   own caption is read as a second signal, then unambiguous brands, then keyword rules.
   Substring traps ("li**mett**e", Milk**ana**, In**sekt**enabwehr) are space-guarded, and
   a keyword that only fires by coincidence is pinned to the product that proved it.

The taxonomy spans **20+ categories**, including Lamb & Other Meat, Eggs, Ready Meals, and
a cross-cutting Vegan section. A CI **self-disagreement gate** flags any product name
served under two categories. It is free to compute and needs no ground truth, because a
classifier that contradicts itself is wrong by construction.

Reviewing all offers cut **"Other" from ~190 to ~2 of 482**. Categories are computed at
scrape time and stored, along with the path, so after tuning you can re-apply them without
re-scraping: `python -m app.scripts.recategorize` (or `POST /api/recategorize`). The app
**hides non-food by default**, with a "+ Non-food" toggle. Guards live in
[`tests/test_categories.py`](backend/tests/test_categories.py) (`pytest`).

## CI/CD (GitHub Actions)

Three workflows under [`.github/workflows/`](.github/workflows/):

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `ci.yml` | push / PR to `main` | Backend `ruff` + `pytest`, mobile ESLint + `tsc`, and a backend Docker image build. On green pushes to `main` it triggers the Render deploy. |
| `eas-update.yml` | after a green CI run on `main` + manual | Publishes an EAS Update (OTA) to the `production` channel — gated on a successful CI run (via `workflow_run`), and only when `mobile/**` changed, so a failing build can't reach users. |
| `scrape.yml` | Sunday cron + manual | Wipes & re-scrapes via `POST /api/reset` (flyers are weekly, spent by Sunday) — retries 3× and opens/comments a self-alerting failure issue. A `verify_only` dispatch input re-checks the deployed data **without** wiping it, so a mid-week fix can clear a stale alert. |

Least-privilege permissions, dependency caching and concurrency cancellation apply
throughout. CI is hermetic: the tests use JSON fixtures, so they need no network and no
secrets.

### One-time setup (to activate deploy + OTA)

The deploy and EAS Update steps **skip quietly** until their secrets exist, so CI is green
out of the box. To turn them on:

**Gated Render deploy** (deploy only when CI is green):
1. Render dashboard → service → **Settings → turn OFF Auto-Deploy**. Otherwise it deploys
   on every push and bypasses the gate.
2. Settings → **Deploy Hook** → copy the URL.
3. GitHub repo → Settings → Secrets and variables → Actions → add
   **`RENDER_DEPLOY_HOOK_URL`**.

**EAS Update (OTA):**
1. expo.dev → Account → **Access Tokens** → create one.
2. Add it as the GitHub secret **`EXPO_TOKEN`**.
3. Run a fresh `eas build -p ios --profile production` once. An OTA update only reaches a
   build that embeds `expo-updates` at the matching runtime version, so the current
   TestFlight build won't receive updates until you rebuild it.

**Branch protection:** two GitHub rulesets govern `main` — *protect history* (no
force-push, no deletion) and *require green PR* (required `Backend` / `Mobile` /
Docker-build checks, squash-only, linear history) — with a scoped admin bypass so
zero-risk docs can still be pushed directly.

Milestone history: [docs/MILESTONES.md](docs/MILESTONES.md).

## Legal

For personal use. The scrapers run at low frequency (weekly), cache aggressively, and
respect each site's terms of service.

## Experience Gained

What building and running this project demonstrates:

- Built an ETL pipeline that pulls 8 retail chains into one schema, and chose the sixth
  source by measuring three candidate feeds against the gate's parse-quality thresholds.
- Audited ~4,000 stored payloads and 2,700 products against their own photos: recovered
  prices for ~21% of offers, lifted €/kg coverage 53% → 72%, reclassified 107 records.
- Wrote ~1,630 backend pytest and ~475 mobile Jest tests behind a `--cov-fail-under=85`
  floor, plus Hypothesis property tests (auto-generated inputs) that found four latent bugs.
- Cut one test file from 20 live third-party HTTP calls to zero (3.4s → 0.28s), and built a
  mutation harness that caught two tests passing for the wrong reason.
- Built a 3-workflow GitHub Actions pipeline that gates the Render deploy and the EAS
  over-the-air release on green CI, and retries the weekly scrape 3× before filing an issue.
- Containerized the FastAPI backend and deployed it from one version-controlled
  `render.yaml` Blueprint, with Alembic migrations spanning SQLite and PostgreSQL.
- Hardened the deployed surface with two GitHub rulesets, SHA-pinned Actions, Dependabot
  cut to CVEs only, a timing-safe admin token, and a non-root container image.
