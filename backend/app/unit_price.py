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


# --- normalizing the source's raw Grundpreis string -------------------------------
# The feed emits the Grundpreis in several shapes; only "1 kg = X" parses (here and in
# the app's fmtPricePerUnit), so the rest are canonicalized on read.
_PAREN = re.compile(r"^\s*\((.*)\)\s*$")  # "(1 kg = 8.05)" -> "1 kg = 8.05"
# A label meaning "the advertised price IS the per-kg / per-100g price", optionally with
# the value already attached ("kg-Preis = 4.98").
_UNIT_LABEL = re.compile(r"^\s*(kg|100\s*-?\s*g)\s*-?\s*preis\s*(?:=\s*(.+))?\s*$", re.IGNORECASE)
# German flyer shorthand: "-.90" / "-,90" means 0.90 (the dash stands in for the euros).
_DASH_PLACEHOLDER = re.compile(r"(?<![\d)])-(?=[.,]\d)")
# ALDI omits the leading amount every other chain prints ("kg = 5.97", "(Liter = 0.99)" vs
# "1 kg = 5.97") and spells the volume unit as a word. Only an *optional literal 1* is
# allowed, never a general number: "100 g = 2.19" / "100g = 39,90" occur in the feed and
# must not be read as a per-kg price. "liter" precedes "l" so the longest unit wins.
_BARE_UNIT = re.compile(r"^\s*(?:1\s*)?(kg|liter|l)\s*=\s*(.+)$", re.IGNORECASE)
# A colon typo'd as the decimal separator ("Liter = 1:75" = 1.75). Substituted before the
# value is read, or the number regex stops at the colon and silently yields 1.00 — and a
# wrong €/l is worse than none.
_COLON_DECIMAL = re.compile(r"(?<=\d):(?=\d)")
# The leading number of a value, dropping any trailing qualifier: "9.58 ATG" (Abtropfgewicht
# = drained weight) -> "9.58", and a range "6.64/5.98" -> "6.64" — already the value both
# `unit_price_cents` and the app's `fmtPricePerUnit` pick, so the card is unchanged. The
# German whole-euro shorthand ("4.-" = 4,00 €) is kept intact so it still reads "4,- €/l".
_LEAD_NUM = re.compile(r"^-?\d+(?:[.,]\d+)?(?:[.,]-)?")


def normalize_price_per_unit(ppu: Optional[str], price_cents: Optional[int]) -> Optional[str]:
    """Canonicalize the source's raw Grundpreis into the "1 kg = X" / "1 l = X" shape.

    `Offer.price_per_unit` mirrors the feed verbatim, and the feed is inconsistent:
      * "(1 kg = 8.05)"  — parenthesized; the anchored `_EQ_RE` can't read it, and the card
        renders it as garbage ("8,05) €/(1 kg"). Unwrapped for every unit, so non-kg/l
        Grundpreise (1 WL / 1 Tab / 1 m²) display right while staying unsortable.
      * "kg-Preis" / "100-g-Preis" — a *label*, not a value: the advertised price IS the
        per-unit price. Rebuilt from `price_cents`; per-100g is normalized to kg (what the
        feed itself does elsewhere: EDEKA's 0,39 € / 100 g cherries carry "1kg = 3,90").
      * "kg-Preis = 4.98" — label with the value attached.
      * "1 kg = -.90"    — German shorthand for 0.90.
      * "kg = 5.97" / "(Liter = 0.99)" — ALDI drops the leading "1" and writes the volume
        unit as a word, so the anchored `_EQ_RE` rejects it (only 2% of ALDI's offers were
        sortable). The string is *truthy*, so it also suppressed the derive fallback.
      * "Liter = 1:75"   — a colon typo'd as the decimal separator.
      * "(kg = 9.58 ATG)" — a trailing drained-weight qualifier on the value.
    Returns None for a label with no usable price, so the caller's `derive_price_per_unit`
    fallback can run instead of being suppressed by a non-null junk string. Unknown shapes
    pass through untouched; already-clean strings are unchanged (idempotent).
    """
    if not ppu:
        return None
    s = ppu.strip()
    paren = _PAREN.match(s)
    if paren:
        s = paren.group(1).strip()
    label = _UNIT_LABEL.match(s)
    if label:
        per_kg = label.group(1).lower().startswith("kg")
        value = label.group(2)
        if value:  # "kg-Preis = 4.98"
            s = f"{'1 kg' if per_kg else '100 g'} = {value.strip()}"
        else:  # bare label -> the sales price is the per-unit price
            if not price_cents or price_cents <= 0:
                return None
            euros = price_cents / 100
            s = f"1 kg = {euros if per_kg else euros * 10:.2f}"
    s = _DASH_PLACEHOLDER.sub("0", s)
    bare = _BARE_UNIT.match(s)
    if bare:
        # Keep the feed's own spelling of an already-valid unit ("1 L = 1.05" stays "L", so
        # the card reads as it always has); only the word "Liter" needs mapping to the axis.
        raw_unit = bare.group(1)
        axis = "l" if raw_unit.lower() == "liter" else raw_unit
        value = _COLON_DECIMAL.sub(".", bare.group(2).strip())
        num = _LEAD_NUM.match(value)
        if num:  # no number -> leave the string alone rather than invent one
            s = f"1 {axis} = {num.group(0)}"
    return s or None


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
