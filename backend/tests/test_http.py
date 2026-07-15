"""Tests for the pacing + retry transport in app/http.py (the polite outbound client).

Uses httpx.MockTransport as the inner transport so no real network is touched, and
monkeypatches time.sleep so backoff/pacing is asserted on the *requested* delay rather
than actually waiting — the suite never sleeps.
"""
from __future__ import annotations

import httpx
import pytest

import app.http as http
from app import metrics


def _client(handler, **kw) -> httpx.Client:
    """A client whose inner transport is a MockTransport driven by `handler`."""
    transport = http._PacedRetryTransport(httpx.MockTransport(handler), **kw)
    return httpx.Client(transport=transport)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Never actually sleep; capture the requested delays instead."""
    slept: list[float] = []
    monkeypatch.setattr(http.time, "sleep", lambda s: slept.append(s))
    return slept


def test_retries_a_429_then_succeeds(_no_sleep):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429 if len(calls) == 1 else 200, text="ok")

    with _client(handler, gap_s=0, jitter_s=0, max_retries=2) as c:
        resp = c.get("https://flyer.test/x")

    assert resp.status_code == 200
    assert len(calls) == 2  # one retry
    assert len(_no_sleep) == 1  # slept once, between the two attempts


def test_honors_retry_after_seconds(_no_sleep):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200)

    with _client(handler, gap_s=0, jitter_s=0, max_retries=2, retry_cap_s=30) as c:
        c.get("https://flyer.test/x")

    assert _no_sleep == [2.0]  # backed off exactly the server-requested 2s


def test_retry_after_is_clamped_to_the_cap(_no_sleep):
    def handler(request):
        return httpx.Response(429, headers={"Retry-After": "9999"})

    with _client(handler, gap_s=0, jitter_s=0, max_retries=1, retry_cap_s=30) as c:
        c.get("https://flyer.test/x")

    assert _no_sleep == [30.0]  # clamped so a hostile Retry-After can't hang the job


def test_honors_retry_after_as_an_http_date(_no_sleep):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            # Retry-After can be an HTTP-date, not just seconds; a far-future one → the cap.
            return httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"})
        return httpx.Response(200)

    with _client(handler, gap_s=0, jitter_s=0, max_retries=2, retry_cap_s=30) as c:
        c.get("https://flyer.test/x")

    assert _no_sleep == [30.0]  # parsed the date and clamped to the cap


def test_gives_up_after_max_retries_and_records_a_throttle(_no_sleep):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429)

    before = metrics.snapshot()["throttled_total"]
    with _client(handler, gap_s=0, jitter_s=0, max_retries=2) as c:
        resp = c.get("https://overpass.test/api")

    # The last response is handed back so the caller's raise_for_status() still fails
    # (→ scraper fail-soft to samples) — but the throttle is now metered, not invisible.
    assert resp.status_code == 429
    assert len(calls) == 3  # initial + 2 retries
    assert metrics.snapshot()["throttled_total"] == before + 1
    assert metrics.snapshot()["throttles"].get("overpass.test", 0) >= 1


def test_does_not_retry_a_403_but_flags_it(_no_sleep):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(403)

    before = metrics.snapshot()["throttled_total"]
    with _client(handler, gap_s=0, jitter_s=0, max_retries=2) as c:
        resp = c.get("https://flyer.test/blocked")

    assert resp.status_code == 403
    assert len(calls) == 1  # a hard block is not retried…
    assert not _no_sleep  # …and there's no backoff sleep
    assert metrics.snapshot()["throttled_total"] == before + 1


def test_a_normal_200_is_neither_retried_nor_flagged(_no_sleep):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, text="hi")

    before = metrics.snapshot()["throttled_total"]
    with _client(handler, gap_s=0, jitter_s=0, max_retries=2) as c:
        resp = c.get("https://flyer.test/ok")

    assert resp.status_code == 200 and resp.text == "hi"
    assert len(calls) == 1
    assert not _no_sleep
    assert metrics.snapshot()["throttled_total"] == before


def test_pacing_waits_the_min_gap(_no_sleep, monkeypatch):
    # Freeze time and pretend a send just happened "now", so the next call must wait the gap.
    monkeypatch.setattr(http.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(http, "_last_send_at", 100.0)

    with _client(lambda r: httpx.Response(200), gap_s=0.5, jitter_s=0.0, max_retries=0) as c:
        c.get("https://flyer.test/x")

    assert _no_sleep == [0.5]  # waited the full gap since the last send


def test_pacing_adds_jitter_on_top_of_the_gap(_no_sleep, monkeypatch):
    monkeypatch.setattr(http.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(http, "_last_send_at", 100.0)
    monkeypatch.setattr(http.random, "uniform", lambda a, b: b)  # deterministic: full jitter

    with _client(lambda r: httpx.Response(200), gap_s=0.5, jitter_s=0.3, max_retries=0) as c:
        c.get("https://flyer.test/x")

    assert _no_sleep == [0.8]  # gap (0.5) + jitter (0.3)


def test_pacing_is_off_when_gap_and_jitter_are_zero(_no_sleep):
    # The suite's default config (see conftest) — no sleeping at all.
    with _client(lambda r: httpx.Response(200), gap_s=0, jitter_s=0, max_retries=0) as c:
        c.get("https://flyer.test/x")

    assert not _no_sleep
