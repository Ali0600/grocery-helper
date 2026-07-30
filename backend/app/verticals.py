"""Which shop *kind* a chain belongs to — the app's two top-level sections.

The app opens on a home screen with two buttons, Grocery and Drugstore, and every
deals surface below that is scoped to one of them. A chain's vertical is a **fact about
the chain**, not about a `Store` row (a Rossmann in any PLZ is still a drugstore), so
this is a frozen constant rather than a DB column — no migration, and it can't drift
per-row. Same shape and spirit as ``store_locator.ACTIVE_CHAINS``.

This module deliberately imports nothing from the app: ``api/offers.py``,
``services/store_locator.py`` and ``scrapers/run.py`` all need it, and a leaf module
keeps that free of import cycles.

**Why the split is load-bearing, not just navigation.** ``/api/offers`` caps at 2000 and
the app loads the whole set. Measured 2026-07-30 for one Berlin PLZ, deduped: grocery is
**1630** (rewe 434, lidl 397, aldi 287, edeka_center 278, edeka 234) and Rossmann adds
**283** — 1913 against the cap, 87 headroom. Scoping each vertical to its own query is
what keeps both comfortably under it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class VerticalSpec:
    label: str
    chains: Tuple[str, ...]
    #: OpenStreetMap tags identifying this kind of shop, for the nearby-store locator.
    #: Supermarkets and drugstores are tagged differently (`shop=chemist` is a German
    #: Drogerie: dm/Rossmann), so a supermarket-only query cannot find them.
    osm_tags: Tuple[str, ...]


VERTICALS: Dict[str, VerticalSpec] = {
    "grocery": VerticalSpec(
        label="Grocery",
        chains=("lidl", "rewe", "edeka", "edeka_center", "aldi"),
        osm_tags=("shop=supermarket",),
    ),
    # dm is NOT here yet: its meinprospekt brochure exists but serves `{"contents": []}`,
    # so the flyer engine can never produce a dm offer. dm only has an online catalog
    # (21k products, everyday prices, no validity window) — a different data model, and
    # its own plan. See CLAUDE.md before re-probing.
    "drugstore": VerticalSpec(
        label="Drugstore",
        chains=("rossmann",),
        osm_tags=("shop=chemist",),
    ),
}

#: chain slug -> vertical slug. Chains are disjoint across verticals by construction.
CHAIN_VERTICAL: Dict[str, str] = {
    chain: vertical for vertical, spec in VERTICALS.items() for chain in spec.chains
}


def chains_for(vertical: str) -> Tuple[str, ...]:
    """The chains in *vertical*, or () if it isn't one we know."""
    spec = VERTICALS.get(vertical)
    return spec.chains if spec else ()
