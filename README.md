# Grocery Helper

Find the best weekly grocery deals near you in Berlin. The app scrapes the
weekly offers ("Angebote") from local supermarket chains, normalizes and
categorizes them, computes the **% discount** for every item, and helps you
build the cheapest basket across one or two stores.

> **Status:** v1 in progress. **Live Lidl offers** + API + the React Native app
> work end-to-end — real Berlin prices, resolved from your postal code via the
> Lidl Plus endpoints. Rewe is next. See [Roadmap](#roadmap).

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
| POST   | `/api/optimize`   | Cheapest basket across 1–2 stores                |
| POST   | `/api/scrape`     | Re-run scrapers on demand (dev)                  |
| POST   | `/api/recategorize` | Re-apply the classifier to stored offers (dev) |

## Scrapers

**Lidl — live.** [`backend/app/scrapers/lidl.py`](backend/app/scrapers/lidl.py)
resolves the nearest store for a postal code via the Lidl Plus store-autocomplete
endpoint, then pulls that store's current offers from `offers.lidlplus.com`. Each
offer carries a struck-through regular price, so exact % discounts are computed
directly. If the endpoint changes or is unreachable, it falls back to sample data
so the app stays up. (Endpoints adapted from
[EvickaStudio/lidl-discounts](https://github.com/EvickaStudio/lidl-discounts).)

**Rewe — next.** Same idea, but behind Cloudflare and may require a client cert
from its app (`mobile-api.rewe.de/api/v3/all-offers?marketCode=…`).

**Categorization.** Offer names are German and brand-heavy, so
[`categories.py`](backend/app/categories.py) classifies each offer in three
layers (first match wins): an **unambiguous brand → category map** (e.g. Allini →
beverages, Mister Choc → sweets, Iglo → frozen, Parkside/Esmara/… → non-food),
then **high-priority override tokens** (sekt, frizzante, secco… → beverages) so a
flavour word like "Mango" can't beat the real category, then the ordered
**German-keyword ruleset**. Categories are computed at scrape time and stored, so
after tuning the rules run the backfill — `python -m app.scripts.recategorize`
(or `POST /api/recategorize`) — to re-apply them to existing rows without
re-scraping. Guard cases live in [`tests/test_categories.py`](backend/tests/test_categories.py)
(`pytest`).

## Roadmap

- [x] Backend pipeline: scrape → normalize → categorize → discount % → store
- [x] API: offers, categories, stores, basket optimizer
- [x] Live Lidl scraper (Lidl Plus store + offers endpoints; PLZ → nearest store)
- [x] React Native app: live deals by category, ranked by % off, with per-offer
      flyer images + tap-to-view (links to Lidl's full weekly Prospekt)
- [ ] Rewe scraper (Cloudflare / market resolution by PLZ)
- [ ] In-app basket optimizer screen (1 vs 2 stores)
- [ ] Scheduled weekly scrape + deploy to PaaS with monitoring/alerts
- [ ] Recipes from on-sale + pantry items (later phase)

## Legal

For personal use. Scrapers run at low frequency (weekly) with aggressive caching
and respect each site's terms of service.
