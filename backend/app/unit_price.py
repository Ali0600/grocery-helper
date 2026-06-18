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


# A Grundpreis the source embedded in the description but never lifted into
# `price_per_unit` (e.g. "… 1 kg = 5.67 150 g"); the amount is always 1 kg / 1 l.
_INLINE_GRUNDPREIS = re.compile(r"\b1\s*(kg|l)\s*=\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
# A numeric quantity + its unit. "kg" before "g" and "ml"/"cl"/"liter" before "l" so
# the longest unit wins; count units (Stück/Stk/St) are included so a *second*
# quantity disqualifies the 1-kg shortcut. The trailing \b keeps "Kl."/"Liter" sane.
_QTY = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*-?\s*(kg|g|ml|cl|liter|l|stück|stk|st)\b", re.IGNORECASE
)


def derive_price_per_unit(unit: Optional[str], price_cents: int) -> Optional[str]:
    """Recover a "1 kg = X" / "1 l = X" string when the source omitted the Grundpreis.

    Two safe cases only: (1) the unit string *embeds* a Grundpreis the scraper didn't
    extract; (2) the item is sold as a single 1 kg / 1 l quantity ("Klasse I 1 kg",
    "je 1-kg-Schale"), so the price itself is the per-unit price. Anything ambiguous —
    a second quantity ("500 g 1 kg" where 1 kg is only a base reference, "1 kg 20
    Stück"), an approximate "Ca. 1,1 kg", or multi-variant ranges — returns None,
    because a wrong €/kg is worse than none. The result feeds `unit_price_cents` and
    the card's `fmtPricePerUnit`.
    """
    if not unit or not price_cents or price_cents <= 0:
        return None
    text = unit.strip()

    inline = _INLINE_GRUNDPREIS.search(text)
    if inline:
        return f"1 {inline.group(1).lower()} = {inline.group(2)}"

    tokens = _QTY.findall(text)
    if len(tokens) == 1:
        num_s, raw_unit = tokens[0]
        try:
            num = float(num_s.replace(",", "."))
        except ValueError:
            return None
        u = "l" if raw_unit.lower() in ("l", "liter") else raw_unit.lower()
        if u in ("kg", "l") and abs(num - 1.0) < 1e-9:
            return f"1 {u} = {price_cents / 100:.2f}"
    return None
