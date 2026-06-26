"""Dump this week's on-sale ingredient candidates as JSON — the deterministic input for
the **offline** recipe-authoring step.

There is no LLM/API here: this just prepares the data. Claude Code (headless, the agent —
not a metered API key) reads this output + the always-have staples and (re)writes
`mobile/src/data/recipes.ts`, which ships to the app via OTA. See `docs/recipes.md`.

Usage (read-only; needs the dev DB seeded for the current week):
    cd backend && source .venv/bin/activate && python -m app.scripts.recipe_seed [--plz 10115]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

from sqlalchemy import select

from ..db import SessionLocal
from ..dedup import dedup_offers
from ..models import Offer

# Categories worth cooking from (skip household / beverages / sweets / snacks).
COOK_CATEGORIES = [
    "vegetables", "fruits", "poultry", "beef", "pork", "fish",
    "cheese", "dairy", "butter", "bakery", "pantry",
]
PER_CATEGORY = 16  # cheapest N distinct products per category


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plz", default=None, help="filter to one store PLZ (optional)")
    parser.add_argument("--per", type=int, default=PER_CATEGORY)
    args = parser.parse_args()

    by: dict[str, list[dict]] = defaultdict(list)
    with SessionLocal() as session:  # keep open: `o.store` is a lazy relationship
        for o in dedup_offers(session.scalars(select(Offer)).all()):
            if args.plz and o.store.plz != args.plz:
                continue
            if o.category not in COOK_CATEGORIES:
                continue
            by[o.category].append(
                {
                    "name": o.name,
                    "chain": o.store.chain,
                    "price_cents": o.price_cents,
                    "price_per_unit": o.price_per_unit,
                    "discount_pct": o.discount_pct,
                }
            )

    out = {
        cat: sorted(by.get(cat, []), key=lambda x: x["price_cents"])[: args.per]
        for cat in COOK_CATEGORIES
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
