"""Tests for outbound-call metrics and the tracked httpx client."""
import httpx

from app import metrics
from app.http import _on_request, tracked_client


def test_record_groups_by_source():
    metrics.begin_run()
    metrics.record("offers.lidlplus.com")
    metrics.record("stores.lidlplus.com")
    metrics.record("www.meinprospekt.de")
    metrics.record("content-viewer-be.meinprospekt.de")
    metrics.record("overpass-api.de")
    lr = metrics.snapshot()["last_run"]
    assert lr["total_calls"] == 5
    assert lr["by_source"]["Lidl Plus (coupons)"] == 2
    assert lr["by_source"]["meinprospekt (flyer)"] == 2
    assert lr["by_source"]["OpenStreetMap Overpass (stores)"] == 1
    assert metrics.snapshot()["total_calls"] >= 5


def test_begin_run_resets_last_run_only():
    metrics.record("offers.lidlplus.com")
    before_total = metrics.snapshot()["total_calls"]
    metrics.begin_run()
    snap = metrics.snapshot()
    assert snap["last_run"]["total_calls"] == 0
    assert snap["total_calls"] == before_total  # cumulative is unaffected


def test_request_hook_records_host():
    metrics.begin_run()
    _on_request(httpx.Request("GET", "https://offers.lidlplus.com/app/api/x"))
    assert metrics.snapshot()["last_run"]["by_host"]["offers.lidlplus.com"] == 1


def test_tracked_client_attaches_the_request_hook():
    c = tracked_client(timeout=5)
    try:
        assert _on_request in c.event_hooks["request"]
    finally:
        c.close()
