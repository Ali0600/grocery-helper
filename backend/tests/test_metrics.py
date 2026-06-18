"""Tests for outbound-call metrics and the tracked httpx client."""
from datetime import datetime

import httpx

from app import metrics
from app.http import _on_request, tracked_client


def test_record_tallies_total_and_groups_by_source():
    before = metrics.snapshot()["total_calls"]
    metrics.record("offers.lidlplus.com")
    metrics.record("stores.lidlplus.com")
    metrics.record("www.meinprospekt.de")
    metrics.record("overpass-api.de")
    snap = metrics.snapshot()
    assert snap["total_calls"] == before + 4  # cumulative, never reset
    assert snap["by_source"]["Lidl Plus (coupons)"] >= 2
    assert snap["by_source"]["meinprospekt (flyer)"] >= 1
    assert snap["by_source"]["OpenStreetMap Overpass (stores)"] >= 1
    assert snap["by_host"]["offers.lidlplus.com"] >= 1


def test_recent_is_newest_first_with_source_and_timestamp():
    metrics.record("www.meinprospekt.de")
    metrics.record("overpass-api.de")  # e.g. opening "Stores"
    recent = metrics.snapshot()["recent"]
    assert recent[0]["host"] == "overpass-api.de"  # newest first
    assert recent[0]["source"] == "OpenStreetMap Overpass (stores)"
    assert recent[1]["host"] == "www.meinprospekt.de"
    datetime.fromisoformat(recent[0]["at"])  # every call carries an ISO timestamp


def test_recent_is_capped():
    for _ in range(metrics._RECENT_MAX + 5):
        metrics.record("overpass-api.de")
    assert len(metrics.snapshot()["recent"]) == metrics._RECENT_MAX


def test_request_hook_records_host():
    _on_request(httpx.Request("GET", "https://offers.lidlplus.com/app/api/x"))
    snap = metrics.snapshot()
    assert snap["recent"][0]["host"] == "offers.lidlplus.com"
    assert snap["by_host"]["offers.lidlplus.com"] >= 1


def test_tracked_client_attaches_the_request_hook():
    c = tracked_client(timeout=5)
    try:
        assert _on_request in c.event_hooks["request"]
    finally:
        c.close()
