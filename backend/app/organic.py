"""Organic ("Bio"/"Öko"/"Organic") detection from an offer's name/brand.

Computed in the serializer (no DB column), like ``validity.py`` / ``unit_price.py`` — so it
applies at serve time with no migration or re-scrape. German flyers mark organic via a
"Bio" token, usually a compound prefix ("Bio Avocado", "Biomilch", "Bioland …", "EDEKA
Bio …"), or via an organic certifier/brand that doesn't always carry "bio" in the name
(Demeter, Naturland, Alnatura, dennree). A leading token boundary avoids substring traps
(e.g. "…symbiose", "antibiotikafrei"); a live survey showed zero such traps. If a false
positive like "biotin" ever appears, add an exclusion set the way ``categories.py`` guards
its keywords.
"""
from __future__ import annotations

import re
from typing import Optional

# Token-boundary (not mid-word) match of an organic marker. `bio`/`öko` also match the
# German compound-prefix form (Biomilch, Ökomilch) because we anchor on the start of a
# token rather than a whole word.
_ORGANIC_RE = re.compile(
    r"(?<![0-9a-zäöüß])(bio|öko|oeko|organic|bioland|demeter|naturland|alnatura|dennree)",
    re.IGNORECASE,
)


def is_organic(name: str, brand: Optional[str] = None) -> bool:
    """True if the offer's name or brand marks it as organic ("Bio")."""
    return bool(_ORGANIC_RE.search(f"{name} {brand or ''}"))
