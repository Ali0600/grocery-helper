"""Refresh the local dev DB with this week's deals — the prerequisite for `recipe_seed`.

Wraps `run_scrapers()` so the weekly recipe automation (`scripts/regenerate-recipes.sh`) can
populate `grocery.db` without the server running. Writes Offer/Store rows (upsert + dedup);
falls back to sample data per-source if an upstream is unreachable (see the scrapers).

Usage:
    cd backend && source .venv/bin/activate && python -m app.scripts.scrape [--plz 10713]
"""
from __future__ import annotations

import argparse

from ..core.config import settings
from ..db import SessionLocal
from ..scrapers.run import run_scrapers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plz", default=None, help="postal code to scrape (default: settings.default_plz)"
    )
    args = parser.parse_args()

    plz = args.plz or settings.default_plz
    with SessionLocal() as session:
        n = run_scrapers(session, plz)
    print(f"scraped {n} offers for PLZ {plz}")


if __name__ == "__main__":
    main()
