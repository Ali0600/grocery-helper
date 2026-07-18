"""Dump this week's on-sale ingredient candidates as JSON — the deterministic input for
the **offline** recipe-authoring step.

There is no LLM/API here: this just prepares the data. Claude Code (headless, the agent —
not a metered API key) reads this output + the always-have staples and (re)writes
`mobile/src/data/recipes.ts`, which ships to the app via OTA. See `docs/recipes.md`.

Candidates are grouped **by chain**:
    {"plz": "10115",
     "by_chain": {"<chain>": {"<category>": [entry, …], …}, …}}

Deliberately there is no flat "cheapest anywhere" view. Authoring from one used to produce
recipes whose ingredients sit in four different shops **by construction** — it picks the
globally cheapest item per category, so the chains scatter. Measured 2026-07-18: of the 10
recipes authored that way, only 3 were fully shoppable at the best single chain (7 were, using
all five). Grouping by chain is what lets the app's "Shop at" scope find anything; a recipe
that spans two stores is authored from the union of exactly two of these lists.

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
PER_CATEGORY = 12  # cheapest N distinct products per category, per chain


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plz", default=None, help="filter to one store PLZ (optional)")
    parser.add_argument("--per", type=int, default=PER_CATEGORY)
    args = parser.parse_args()

    by_chain: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    with SessionLocal() as session:  # keep open: `o.store` is a lazy relationship
        for o in dedup_offers(session.scalars(select(Offer)).all()):
            if args.plz and o.store.plz != args.plz:
                continue
            if o.category not in COOK_CATEGORIES:
                continue
            by_chain[o.store.chain][o.category].append(
                {
                    "name": o.name,
                    "chain": o.store.chain,
                    "price_cents": o.price_cents,
                    "price_per_unit": o.price_per_unit,
                    "discount_pct": o.discount_pct,
                }
            )

    out = {
        # Carried through so the authoring step stamps `generatedFor` from the data it actually
        # read, rather than a PLZ hardcoded in the prompt (SCRAPE_PLZ is configurable).
        "plz": args.plz,
        # Every cookable category is listed per chain even when empty, so the authoring step
        # can see "this chain has no beef this week" instead of inferring it from a gap.
        "by_chain": {
            chain: {
                cat: sorted(by_chain[chain][cat], key=lambda x: x["price_cents"])[: args.per]
                for cat in COOK_CATEGORIES
            }
            for chain in sorted(by_chain)
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
