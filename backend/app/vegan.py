"""Vegan detection from an offer's name/brand.

Used by ``categories.py`` to route explicitly-vegan products into the **"vegan"** category
(the user's choice: vegan is its own section, so a vegan cheese moves out of Cheese). German
flyers mark vegan via the word "vegan" (vegan/vegane/veganes/veganer), "pflanzlich"
(plant-based), or a vegan-only brand (Vemondo is Lidl's vegan line). A leading token boundary
avoids mid-word matches; verified against the live catalog (the only "pflanzlich" items were
real plant-based products, not plant oil). Brands are **vegan-only** — mixed brands that sell
both meat and vegan (e.g. Rügenwalder) are intentionally excluded so their meat isn't moved.
"""
from __future__ import annotations

import re
from typing import Optional

_VEGAN_RE = re.compile(
    r"(?<![a-zäöüß])(vegan|pflanzlich)"
    r"|(?<![a-zäöüß])(vemondo|vemodo|like meat|likemeat|next level|garden gourmet|"
    r"beyond meat|vivera|endori|veganz|alpro|taifun|planted|heura)",
    re.IGNORECASE,
)


def is_vegan(name: str, brand: Optional[str] = None) -> bool:
    """True if the offer's name or brand marks it as vegan / plant-based."""
    return bool(_VEGAN_RE.search(f"{name} {brand or ''}"))
