"""In-memory counters for outbound HTTP calls to the scraped websites.

Browsing the app hits only our DB; external calls happen when we **scrape** (cold
start / set-PLZ) or resolve **nearby stores** (Overpass). Every outbound request
is counted by host via an httpx request hook (see `app/http.py`) and surfaced at
`GET /api/scrape-stats`, so you can see how chatty a run is — the sites
soft-throttle bursts. Counts are process-local and reset on restart.
"""
from __future__ import annotations

import threading
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, Optional

_lock = threading.Lock()
_total: Counter = Counter()  # host -> calls since server start
_run: Counter = Counter()  # host -> calls in the most recent scrape run
_run_started_at: Optional[datetime] = None
_started_at = datetime.now(timezone.utc)


def record(host: str) -> None:
    """Count one outbound request to `host` (called from the httpx request hook)."""
    with _lock:
        _total[host] += 1
        _run[host] += 1


def begin_run() -> None:
    """Mark the start of a scrape run so its outbound calls can be reported alone."""
    global _run, _run_started_at
    with _lock:
        _run = Counter()
        _run_started_at = datetime.now(timezone.utc)


def _source(host: str) -> str:
    """Group a host under the friendly data source it belongs to."""
    h = host.lower()
    if "lidlplus.com" in h:
        return "Lidl Plus (coupons)"
    if "meinprospekt.de" in h:
        return "meinprospekt (flyer)"
    if "overpass" in h or "maps.mail.ru" in h:
        return "OpenStreetMap Overpass (stores)"
    return host


def _by_source(counter: Counter) -> Dict[str, int]:
    grouped: Counter = Counter()
    for host, n in counter.items():
        grouped[_source(host)] += n
    return dict(grouped)


def snapshot() -> dict:
    """Totals since startup plus the most recent scrape run, by source and host."""
    with _lock:
        return {
            "since": _started_at.isoformat(),
            "total_calls": sum(_total.values()),
            "by_source": _by_source(_total),
            "by_host": dict(_total),
            "last_run": {
                "at": _run_started_at.isoformat() if _run_started_at else None,
                "total_calls": sum(_run.values()),
                "by_source": _by_source(_run),
                "by_host": dict(_run),
            },
        }
