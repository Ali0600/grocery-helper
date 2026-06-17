"""Normalize a per-unit price string to a comparable number for sorting.

`Offer.price_per_unit` is the source's raw Grundpreis string — almost always
"1 kg = 13.33" or "1 l = 2.47" (German Grundpreis is per 1 kg / 1 l), plus a few
Lidl variants like the bare "22.79 €/kg". We collapse weight (€/kg) and volume
(€/l) onto one comparable axis — the standard Grundpreis convention — so a
category like beef can be ranked cheapest-first. Per-piece ("Stück"),
per-wash-load ("wl"), ranges' later values, and unparseable strings yield None
(they sink under the €/kg sort rather than ranking wrongly).
"""
from __future__ import annotations

import re
from typing import Optional

# "1 kg = 13.33" / "1 l = 2.47" — the amount is always 1 in the data; for a range
# ("1 kg = 9.97/10.83") we capture the first value (matches what the card shows).
_EQ_RE = re.compile(r"^\s*1\s*(kg|l)\b.*?=\s*(-?\d+(?:[.,]\d+)?)")
# bare "22.79 €/kg" (or ".. /kg") with no "1 kg =" prefix.
_SLASH_RE = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*€?\s*/\s*(kg|l)\b")


def unit_price_cents(ppu: Optional[str]) -> Optional[int]:
    """Cents per kg (weight) or per litre (volume); None if not comparable."""
    if not ppu:
        return None
    s = ppu.strip().lower()
    base = value = None
    m = _EQ_RE.match(s)
    if m:
        base, value = m.group(1), m.group(2)
    else:
        m = _SLASH_RE.search(s)
        if m:
            value, base = m.group(1), m.group(2)
    if base not in ("kg", "l") or value is None:
        return None
    try:
        v = float(value.replace(",", "."))
    except ValueError:
        return None
    return round(v * 100) if v > 0 else None
