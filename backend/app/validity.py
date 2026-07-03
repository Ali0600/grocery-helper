"""Day-validity helpers: a short label + a "day-limited" flag from an offer's
``valid_from``/``valid_to`` dates.

Computed in the serializer (no DB column), like ``unit_price.py``. Many flyer deals are
on sale only on certain days (a Lidl Thu–Sat "Wochenend-Kracher", a Friday-only special);
the scraper now stores the real per-offer window, and these turn it into something the app
can badge ("Do–Sa") and filter ("valid today").
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

_BERLIN = ZoneInfo("Europe/Berlin")


def berlin_today() -> date:
    """Today in the shops' timezone. The server runs UTC (Render), so a naive
    ``date.today()`` is yesterday for up to 2 hours after Berlin midnight — long
    enough for expired offers to linger (or fresh ones to be dropped) around the
    boundary. All validity comparisons should use this."""
    return datetime.now(_BERLIN).date()

# German weekday abbreviations, Monday-first (matches date.weekday()).
_DOW = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
# The normal German trading week is Mon–Sat (6 days; shops shut Sunday). A window shorter
# than that is a day-limited special (a weekend Do–Sa, a Fr-only deal, …); Mon–Sat and the
# odd long-running list (>= a week) are "valid all week" -> not badged.
_FULL_WEEK_DAYS = 6


def is_day_limited(valid_from: Optional[date], valid_to: Optional[date]) -> bool:
    """True if the offer is valid for fewer days than the normal Mon–Sat week."""
    if not valid_from or not valid_to or valid_to < valid_from:
        return False
    return (valid_to - valid_from).days + 1 < _FULL_WEEK_DAYS


def valid_days_label(valid_from: Optional[date], valid_to: Optional[date]) -> Optional[str]:
    """A compact day-range label for a day-limited offer ("Do–Sa", or "Fr" for a single
    day); None when the offer is valid the whole week (no badge)."""
    if not is_day_limited(valid_from, valid_to):
        return None
    start, end = _DOW[valid_from.weekday()], _DOW[valid_to.weekday()]
    return start if start == end else f"{start}–{end}"  # "Fr" or "Do–Sa"
