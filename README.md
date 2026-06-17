# Grocery Helper

Find the best weekly grocery deals near you in Berlin. The app scrapes the
weekly offers ("Angebote") from local supermarket chains, normalizes and
categorizes them, computes the **% discount** for every item, and helps you
build the cheapest basket across one or two stores.

> **Status:** v1 in progress. **Live Lidl + REWE offers** + API + the React
> Native app work end-to-end — real Berlin prices, resolved from your postal
> code via the Lidl Plus endpoints and the meinprospekt weekly-flyer feed. Two
> chains make the basket optimizer meaningful. See [Roadmap](#roadmap).

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
- **Cross-platform mobile client** — a React Native (Expo) app consuming the API
  to browse local deals by category, sorted by savings.
- **Containerized, deployable stack** — Dockerized backend with Docker Compose +
  PostgreSQL, designed for CI/CD deployment to a PaaS with scraper health
  monitoring and alerting.
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
- [x] Nearby-stores directory ("Stores"): nearest Lidl/REWE/Edeka/Aldi/Netto/
      Penny/Kaufland with addresses (OpenStreetMap), add non-active chains to a
      saved "My stores" list — groundwork for onboarding more chains
- [ ] In-app basket optimizer screen (1 vs 2 stores)
- [ ] Scheduled weekly scrape + deploy to PaaS with monitoring/alerts
- [ ] Recipes from on-sale + pantry items (later phase)

## Legal

For personal use. Scrapers run at low frequency (weekly) with aggressive caching
and respect each site's terms of service.
