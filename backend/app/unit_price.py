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
# Markers that make a single net weight unsafe to divide into a €/kg:
#   - a multipack ("3x 400 ml", "20 × 10 g") — the printed unit isn't the net amount
#   - an approximate weight ("Ca. 1,1 kg") — a divided €/kg would be fake-precise
#   - a numeric range / ratio ("250-300 g", "1,2/1,1 kg") — which value to divide by?
# (A lone hyphenated weight like "500-g-Schale" is fine: the range rule needs a digit on
# *both* sides of the separator, so "1-kg" / "500-g" aren't flagged.)
_DIVIDE_TRAP = re.compile(
    r"\d\s*[x×]\s*\d"
    r"|\bca\.?\b|\bcirca\b"
    r"|\d+(?:[.,]\d+)?\s*[-–/]\s*\d",
    re.IGNORECASE,
)


def derive_price_per_unit(unit: Optional[str], price_cents: int) -> Optional[str]:
    """Recover a "1 kg = X" / "1 l = X" string when the source omitted the Grundpreis.

    Three cases, all conservative:
      1. the unit string *embeds* a Grundpreis the scraper didn't extract;
      2. the item is sold as a single net weight/volume ("500-g-Schale", "Klasse I 1 kg",
         "2,5 l") — divide the price by that amount (in kg / l) to get the €/kg or €/l;
      3. anything ambiguous returns None, because a wrong €/kg is worse than none: a second
         quantity ("500 g 1 kg", "900 g 30 Stück"), a multipack ("3x 400 ml"), an
         approximate ("Ca. 1,1 kg"), a range ("250-300 g"), or a per-piece unit ("6 Stück").

    The result feeds `unit_price_cents` and the card's `fmtPricePerUnit`.
    """
    if not unit or not price_cents or price_cents <= 0:
        return None
    text = unit.strip()

    # 1. A Grundpreis the source embedded in the text but never lifted into the field.
    inline = _INLINE_GRUNDPREIS.search(text)
    if inline:
        return f"1 {inline.group(1).lower()} = {inline.group(2)}"

    # 2. Divide the price by a single net weight/volume. Bail on any trap, and require
    #    exactly one quantity token (a second one — incl. a "Stück" count — is ambiguous).
    if _DIVIDE_TRAP.search(text):
        return None
    tokens = _QTY.findall(text)
    if len(tokens) != 1:
        return None
    num_s, raw_unit = tokens[0]
    try:
        num = float(num_s.replace(",", "."))
    except ValueError:
        return None
    if num <= 0:
        return None
    euros = price_cents / 100
    u = raw_unit.lower()
    # Normalize the amount to kg (weight) or litres (volume), then price ÷ amount.
    if u == "kg":
        per, axis = euros / num, "kg"
    elif u == "g":
        per, axis = euros / (num / 1000), "kg"
    elif u in ("l", "liter"):
        per, axis = euros / num, "l"
    elif u == "ml":
        per, axis = euros / (num / 1000), "l"
    elif u == "cl":
        per, axis = euros / (num / 100), "l"
    else:
        return None  # stück / stk / st -> no €/kg|€/l axis
    return f"1 {axis} = {per:.2f}"
