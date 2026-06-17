"""Tests for the OSM nearby-store locator. The selection logic is pure and runs
against a saved, hand-crafted Overpass fixture so we never hit the live API."""
import json
import os

from app.services import store_locator as sl
from app.services.store_locator import _chain_for, _haversine, _select_nearest, nearby_stores

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "overpass_stores.json")
CENTER = (52.5, 13.4)  # the fixture's coords are laid out relative to this


def _stores():
    with open(FIXTURE, encoding="utf-8") as f:
        elements = json.load(f)["elements"]
    return _select_nearest(elements, *CENTER)


def test_one_entry_per_known_chain():
    chains = sorted(s.chain for s in _stores())
    assert chains == ["aldi", "edeka", "kaufland", "lidl", "netto", "penny", "rewe"]


def test_excludes_non_allowlisted_markets():
    names = " ".join(s.name.lower() for s in _stores())
    assert "denns" not in names and "go asia" not in names  # bio / local markets dropped


def test_picks_nearest_branch_of_a_chain():
    edeka = next(s for s in _stores() if s.chain == "edeka")
    assert edeka.distance_m < 500  # the ~130m branch, not the ~1.3km "EDEKA Far"
    assert edeka.address and "Hauptstraße 10" in edeka.address


def test_brand_alias_normalization():
    by = {s.chain: s for s in _stores()}
    assert by["aldi"].label == "Aldi"      # from OSM brand "Aldi Nord"
    assert by["netto"].chain == "netto"    # from "Netto Marken-Discount"


def test_store_without_address_is_still_listed():
    rewe = next(s for s in _stores() if s.chain == "rewe")  # "REWE City", no addr tags
    assert rewe.address is None
    assert rewe.active is True


def test_active_flags():
    by = {s.chain: s for s in _stores()}
    assert by["lidl"].active and by["rewe"].active
    assert not by["edeka"].active and not by["kaufland"].active


def test_way_element_parsed_via_center():
    kaufland = next(s for s in _stores() if s.chain == "kaufland")
    assert kaufland.lat and kaufland.lng  # came from the way's `center`, not lat/lon


def test_result_sorted_by_distance():
    dists = [s.distance_m for s in _stores()]
    assert dists == sorted(dists)


def test_haversine_metres():
    # 0.001 degrees of latitude is ~111 m anywhere.
    assert 100 < _haversine(52.5, 13.4, 52.501, 13.4) < 125


def test_chain_for_aliases_and_misses():
    assert _chain_for("Aldi Süd", None) == "aldi"
    assert _chain_for("Netto Marken-Discount", None) == "netto"
    assert _chain_for(None, "REWE City") == "rewe"   # falls back to name when no brand
    assert _chain_for("Denns BioMarkt", None) is None
    assert _chain_for(None, "Go Asia") is None


def test_returns_empty_when_all_mirrors_fail(monkeypatch):
    monkeypatch.setattr(sl, "_fetch_overpass", lambda query, client: None)
    # Uncached coords + an injected (unused) client so no real network happens.
    assert nearby_stores(1.234, 5.678, client=object()) == []
