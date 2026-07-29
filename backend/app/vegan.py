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
    r"|(?<![a-zäöüß])(vemondo|vemodo|like meat|likemeat|like döner|next level|garden gourmet|"
    # `vly` is a pea-protein dairy-alternative brand; its "Joghurt Alternative" was served as
    # Dairy because layer 2's `joghurt` form word fired. Layer 0 beats that. The lookbehind
    # keeps it from firing inside a longer word.
    r"beyond meat|vivera|endori|veganz|alpro|taifun|planted|heura|simply v|oatly|vly)",
    re.IGNORECASE,
)


def vegan_match(name: str, brand: Optional[str] = None) -> Optional[str]:
    """The literal that marked this vegan ("Pflanzlich", "Oatly"), else None — for the trace.

    Matches the RAW string (the regex is IGNORECASE), so the answer keeps the product's own
    casing. Don't lowercase it, and don't feed this `categories._haystack`: that blob is
    lowercased *and* space-padded, and `_VEGAN_RE`'s left-boundary lookbehind is not
    obviously inert under padding.
    """
    m = _VEGAN_RE.search(f"{name} {brand or ''}")
    return m.group(0) if m else None


def is_vegan(name: str, brand: Optional[str] = None) -> bool:
    """True if the offer's name or brand marks it as vegan / plant-based."""
    return vegan_match(name, brand) is not None
