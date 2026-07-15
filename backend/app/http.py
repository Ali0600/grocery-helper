"""A shared httpx client that is polite to the scraped sites.

Every scraper/locator builds its client here, so this one place gives all outbound
traffic three properties:

* **Counted** — an httpx `request` event hook tallies each call by host (`app/metrics.py`).
* **Paced** — a custom transport spaces calls by a global minimum gap + jitter, so a
  scrape's ~15 requests don't hit a flyer aggregator as one datacenter-IP burst (the
  exact shape these sites soft-throttle).
* **Backed off** — the transport retries a 429/502/503/504 a few times, honoring
  `Retry-After`, and records a throttle event when it gives up (or on a 403) so a
  rate-limit stops hiding behind the scrapers' "serve sample data on failure" fallback.

Pacing/retry parameters live in `settings` (`scrape_request_gap_s`, …); tests set the
gap+jitter to 0 (see `tests/conftest.py`) so the suite never sleeps.
"""
from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import httpx

from . import metrics
from .core.config import settings

# 429 = rate limited; 502/503/504 = transient upstream/proxy hiccups. All are worth a
# short backoff+retry. Other 4xx (esp. 403) are hard "no" answers — retrying just adds
# load, so we surface them but don't hammer.
_RETRY_STATUSES = frozenset({429, 502, 503, 504})

# Global pacing state, shared across every tracked client so a scrape that builds a
# fresh client per chain is still spaced end-to-end (process-local; matches the single
# free-tier worker).
_pace_lock = threading.Lock()
_last_send_at = 0.0  # time.monotonic() of the last (reserved) outbound send


def _on_request(request: httpx.Request) -> None:
    metrics.record(request.url.host)


def _drain(response: httpx.Response) -> None:
    """Release a response we're about to discard on retry, so its connection frees up."""
    try:
        response.read()
    except Exception:
        pass
    finally:
        response.close()


class _PacedRetryTransport(httpx.BaseTransport):
    """Wraps an inner transport to pace + back off every send. Testable by passing a
    ``httpx.MockTransport`` as ``inner``."""

    def __init__(
        self,
        inner: Optional[httpx.BaseTransport] = None,
        *,
        gap_s: Optional[float] = None,
        jitter_s: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_cap_s: Optional[float] = None,
        backoff_base_s: float = 1.0,
    ) -> None:
        self._inner = inner if inner is not None else httpx.HTTPTransport()
        self._gap = settings.scrape_request_gap_s if gap_s is None else gap_s
        self._jitter = settings.scrape_request_jitter_s if jitter_s is None else jitter_s
        self._max_retries = settings.scrape_max_retries if max_retries is None else max_retries
        self._retry_cap = settings.scrape_retry_cap_s if retry_cap_s is None else retry_cap_s
        self._backoff_base = backoff_base_s

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = None
        for attempt in range(self._max_retries + 1):
            self._pace()
            response = self._inner.handle_request(request)
            status = response.status_code
            if status not in _RETRY_STATUSES:
                if status == 403:
                    # A hard block won't yield to retries; make it visible, don't hammer.
                    metrics.record_throttle(request.url.host, status)
                return response
            if attempt == self._max_retries:
                # Out of retries on a throttle status. Hand the caller the last response
                # (its raise_for_status() fails → the scraper's fail-soft to samples), but
                # metered so the throttle isn't invisible.
                metrics.record_throttle(request.url.host, status)
                return response
            delay = self._retry_after(response)
            if delay is None:
                delay = self._backoff(attempt)
            _drain(response)
            time.sleep(delay)
        return response  # pragma: no cover - loop always returns

    def close(self) -> None:
        self._inner.close()

    # -- helpers --------------------------------------------------------------

    def _pace(self) -> None:
        """Sleep until at least gap+jitter seconds have elapsed since the last send,
        globally. A no-op when both are 0 (tests)."""
        if self._gap <= 0 and self._jitter <= 0:
            return
        global _last_send_at
        with _pace_lock:
            now = time.monotonic()
            wait = max(0.0, _last_send_at + self._gap - now)
            if self._jitter > 0:
                wait += random.uniform(0, self._jitter)
            _last_send_at = now + wait  # reserve the slot before releasing the lock
        if wait > 0:
            time.sleep(wait)

    def _backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter, capped, when there's no Retry-After."""
        base = self._backoff_base * (2 ** attempt)
        return min(base + random.uniform(0, self._backoff_base), self._retry_cap)

    def _retry_after(self, response: httpx.Response) -> Optional[float]:
        """Seconds to wait per the Retry-After header (integer seconds OR an HTTP-date),
        clamped to [0, retry_cap]. None if the header is absent or unparseable → caller
        falls back to exponential backoff."""
        raw = response.headers.get("retry-after")
        if not raw:
            return None
        raw = raw.strip()
        try:
            return max(0.0, min(float(raw), self._retry_cap))
        except ValueError:
            pass
        try:
            when = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
        if when is None:
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        secs = (when - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, min(secs, self._retry_cap))


def tracked_client(*, timeout: float, headers: Optional[dict] = None) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
        event_hooks={"request": [_on_request]},
        transport=_PacedRetryTransport(),
    )
