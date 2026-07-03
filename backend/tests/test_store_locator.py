"""Tests for the OSM nearby-store locator. The selection logic is pure and runs
against a saved, hand-crafted Overpass fixture so we never hit the live API."""
import json
import os

from app.services import store_locator as sl
from app.services.store_locator import _chain_for, _haversine, _select_nearest, nearby_stores

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "overpass_stores.json")
CENTER = (52.5, 13.4)  # the fixture's coords are laid out relative to this


def _elements():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)["elements"]


def _stores():
    return _select_nearest(_elements(), *CENTER)


def test_one_entry_per_known_chain():
    chains = sorted(s.chain for s in _stores())
    # The fixture's E center carries brand="EDEKA" + a hyphenated name — the two real
    # OSM patterns that used to misclassify — and must surface as its own chain row.
    assert chains == ["aldi", "edeka", "edeka_center", "kaufland", "lidl", "netto", "penny", "rewe"]


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
    assert by["lidl"].active and by["rewe"].active and by["edeka"].active
    assert not by["kaufland"].active and not by["aldi"].active  # not scraped yet


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


def test_chain_for_ecenter_vs_edeka():
    # E center's specific prefixes win (it's listed before "edeka"); a plain EDEKA
    # brand doesn't start with them, so it still classifies as edeka.
    assert _chain_for("E center", None) == "edeka_center"
    assert _chain_for("EDEKA Center", None) == "edeka_center"
    assert _chain_for("EDEKA", None) == "edeka"
    assert _chain_for(None, "Edeka Wolff") == "edeka"


def test_chain_for_ecenter_real_osm_variants():
    # Hyphenated spellings are common in OSM and must not fall through to edeka/None.
    assert _chain_for("E-Center", None) == "edeka_center"
    assert _chain_for("EDEKA-Center", None) == "edeka_center"
    assert _chain_for(None, "E-center Musterstadt") == "edeka_center"
    # The critical masking case: an E center carrying the parent brand tag. The chain
    # loop runs outermost, so edeka_center's prefixes see the NAME before the generic
    # "edeka" prefix can swallow the BRAND.
    assert _chain_for("EDEKA", "E center Musterstadt") == "edeka_center"
    assert _chain_for("EDEKA", "E-Center am Park") == "edeka_center"
    # ...while a regular EDEKA with the same brand tag stays edeka.
    assert _chain_for("EDEKA", "EDEKA Wolff") == "edeka"


def test_returns_empty_when_all_mirrors_fail(monkeypatch):
    monkeypatch.setattr(sl, "_fetch_overpass", lambda query, client: None)
    # Uncached coords + an injected (unused) client so no real network happens.
    assert nearby_stores(1.234, 5.678, client=object()) == []


# --- "Change branch" picker: list every branch of a chain ---------------------


def test_all_branches_keeps_every_store_sorted_by_distance():
    branches = sl._all_branches(_elements(), *CENTER)
    edeka = [s for s in branches if s.chain == "edeka"]
    assert len(edeka) == 2  # the ~130 m branch AND "EDEKA Far" (nearest-scan keeps 1)
    dists = [s.distance_m for s in branches]
    assert dists == sorted(dists)


def test_all_branches_dedupes_one_store_mapped_as_node_and_way():
    els = _elements()
    near = min(
        (e for e in els if _chain_for((e.get("tags") or {}).get("brand"),
                                      (e.get("tags") or {}).get("name")) == "edeka"),
        key=lambda e: _haversine(*CENTER, e["lat"], e["lon"]),
    )
    # The same store re-mapped as a building way (center at the same coords/tags).
    dup = {"type": "way", "center": {"lat": near["lat"], "lon": near["lon"]}, "tags": near["tags"]}
    edeka = [s for s in sl._all_branches(els + [dup], *CENTER) if s.chain == "edeka"]
    assert len(edeka) == 2  # the dup collapses; still just the near branch + "Far"


def test_chain_branches_filters_to_one_chain_and_limits(monkeypatch):
    monkeypatch.setattr(sl, "_fetch_overpass", lambda query, client: _elements())
    sl._BRANCH_CACHE.clear()
    res = sl.chain_branches("edeka", *CENTER, client=object())
    assert res and all(s.chain == "edeka" for s in res)
    assert [s.distance_m for s in res] == sorted(s.distance_m for s in res)
    assert len(res) == 2
    one = sl.chain_branches("edeka", *CENTER, limit=1, client=object())
    assert len(one) == 1 and one[0].distance_m == res[0].distance_m  # nearest kept


def test_chain_branches_unknown_chain_is_empty():
    assert sl.chain_branches("denns", *CENTER, client=object()) == []


# --- PLZ centroid geocoding (picker centre) — no live API --------------------


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, data):
        self._data = data
        self.calls = 0

    def get(self, url, params=None):
        self.calls += 1
        return _FakeResp(self._data)

    def close(self):
        pass


def test_plz_centroid_parses_and_caches():
    sl._PLZ_CACHE.clear()
    fc = _FakeClient([{"lat": "52.48509", "lon": "13.31325"}])
    assert sl.plz_centroid("10115", client=fc) == (52.48509, 13.31325)
    assert fc.calls == 1
    # second lookup is served from cache (no request), even with a would-be-empty client
    assert sl.plz_centroid("10115", client=_FakeClient([])) == (52.48509, 13.31325)


def test_plz_centroid_empty_or_bad_is_none():
    sl._PLZ_CACHE.clear()
    assert sl.plz_centroid("99999", client=_FakeClient([])) is None
    assert sl.plz_centroid("00000", client=_FakeClient([{"lat": "x", "lon": "y"}])) is None
