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
**1630** (rewe 434, lidl 397, aldi 287, edeka_center 278, edeka 234), Rossmann adds
**283** and dm **214** — 2127, i.e. **past the cap if it were one query**. Scoping each
vertical to its own query is the only reason both fit.

Penny joined the grocery vertical on 2026-08-11 at a measured 255 deduped offers, taking it
to ~1885 — still under the cap, which is exactly why Penny was chosen over Netto (461 raw)
and Kaufland (723 raw). Both of those cross it, and truncation happens AFTER a discount sort
with nulls last, so the rows dropped would be disproportionately the chains that publish no
strike price. Raising the cap is the prerequisite for a seventh chain; see
``docs/DECISIONS.md``.

That is also why ``/api/offers`` now defaults to **grocery** when no ``vertical`` is
given, instead of returning every chain (see ``api/offers.py``). Only app builds older
than the vertical release omit it, and those predate Drugstore entirely — they have no UI
for it, so serving them a truncated all-chains list was both over the cap and wrong.
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
        chains=("lidl", "rewe", "edeka", "edeka_center", "aldi", "penny"),
        osm_tags=("shop=supermarket",),
    ),
    # dm is here via its **clearance** feed, not a flyer. Its meinprospekt brochure serves
    # `{"contents": []}` and always will (don't re-probe), and its 21k-product catalog is
    # everyday pricing with no discount or validity — still not a deals source. But the
    # catalog's `isSellout=true` facet is: 214 in-store items, every one with a struck
    # price. See `scrapers/dm.py`.
    "drugstore": VerticalSpec(
        label="Drugstore",
        chains=("rossmann", "dm"),
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
