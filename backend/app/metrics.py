"""In-memory counters for outbound HTTP calls to the scraped websites.

Browsing the app hits only our DB; external calls happen when we **scrape** (cold
start / set-PLZ) or resolve **nearby stores** (Overpass). Every outbound request
is counted by host via an httpx request hook (see `app/http.py`) and surfaced at
`GET /api/scrape-stats`, so you can see how chatty a run is — the sites
soft-throttle bursts. Counts are process-local and reset on restart.
"""
from __future__ import annotations

import threading
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Deque, Dict

_RECENT_MAX = 20  # how many of the latest calls /api/scrape-stats keeps

_lock = threading.Lock()
_total: Counter = Counter()  # host -> calls since server start
_recent: Deque[dict] = deque(maxlen=_RECENT_MAX)  # latest calls, oldest -> newest
_started_at = datetime.now(timezone.utc)


def record(host: str) -> None:
    """Count one outbound request to `host` (called from the httpx request hook)."""
    with _lock:
        _total[host] += 1
        _recent.append(
            {"at": datetime.now(timezone.utc), "host": host, "source": _source(host)}
        )


def _source(host: str) -> str:
    """Group a host under the friendly data source it belongs to."""
    h = host.lower()
    if "lidlplus.com" in h:
        return "Lidl Plus (coupons)"
    if "meinprospekt.de" in h:
        return "meinprospekt (flyer)"
    if "overpass" in h or "maps.mail.ru" in h:
        return "OpenStreetMap Overpass (stores)"
    if "nominatim" in h:
        return "OpenStreetMap Nominatim (PLZ lookup)"
    return host


def _by_source(counter: Counter) -> Dict[str, int]:
    grouped: Counter = Counter()
    for host, n in counter.items():
        grouped[_source(host)] += n
    return dict(grouped)


def snapshot() -> dict:
    """Totals since startup plus the latest individual calls, newest first."""
    with _lock:
        recent = [
            {"at": e["at"].isoformat(), "host": e["host"], "source": e["source"]}
            for e in reversed(_recent)
        ]
        return {
            "since": _started_at.isoformat(),
            "total_calls": sum(_total.values()),
            "by_source": _by_source(_total),
            "by_host": dict(_total),
            "recent": recent,
        }
