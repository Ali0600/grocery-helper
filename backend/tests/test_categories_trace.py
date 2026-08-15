"""Tests for `categories.explain()` — the per-layer trace behind "Why this category?".

The trace exists to be TRUSTED when adjudicating a miscategorization, so the tests here
are mostly about the one thing that would quietly ruin it: `explain` and `classify`
disagreeing about which rule won. T1/T2 are those gates; T6 protects the short-circuit
that keeps `classify` cheap on the scrape path.

Every fixture below was read off the real tables (not invented) — see the PR for the
capture run.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app import categories as C
from app.categories import _FORM_OVERRIDES, FOOD_ROOT, classify, explain
from app.vegan import is_vegan, vegan_match

LAYER_ORDER = ["0", "1", "2", "2b", "3", "4", "5", "6", "7"]


def _rule_tokens() -> list[str]:
    """Every literal the classifier can match, harvested from the tables themselves.

    Generated rather than hand-listed so the corpus GROWS the moment someone adds a rule —
    a fixed list would silently stop covering new layers' entries.
    """
    tokens: list[str] = []
    for table in (C._FORM_OVERRIDES, C._CAPTION_SIGNALS, C._OVERRIDES, C._RULES):
        for _slug, entries in table:
            tokens.extend(entries)
    tokens.extend(C.BRAND_CATEGORY)
    for entries in C._FOOD_RESCUE.values():
        tokens.extend(entries)
    tokens.extend(C._RESCUE_VETO)
    tokens.extend(["vegan", "pflanzlich", "Oatly", "Vemondo", "zzz nothing matches zzz"])
    return tokens


def _generated_cases() -> list[tuple]:
    """The harvested tokens crossed with the path/unit shapes that switch layers on and off."""
    paths = [None, [FOOD_ROOT, "käse"], ["Tierbedarf", "Marken für Tiere"], []]
    # The last one carries a `_PRESERVED_CAPTION` token deliberately. Without a caption that
    # can trigger the post-layer redirect, this whole generated corpus cannot tell a redirect
    # applied in `classify` from one applied in both — the drift it exists to catch. (T2, which
    # would also catch it, is skipped in CI because *.db is gitignored, so this is the only
    # surface that runs there.)
    units = [None, "500 g", "45 % Fett i.Tr.", "Abtropfgewicht (ATG) = 320 g 580-ml-Glas"]
    cases: list[tuple] = []
    for i, token in enumerate(_rule_tokens()):
        cases.append((token, None, paths[i % len(paths)], units[i % len(units)]))
        cases.append((token.upper(), "Ja!", paths[(i + 1) % len(paths)], None))
    # Every known taxonomy node as a real food path, so layer 3 is exercised end to end.
    cases.extend((f"Produkt {node}", None, [FOOD_ROOT, node], None) for node in C._PATH_MAP)
    return cases


# --- T1/T2: the no-drift gates -------------------------------------------------------


def test_explain_and_classify_agree_over_the_generated_corpus():
    """The gate. `explain` must never disagree with `classify` about the winning slug."""
    cases = _generated_cases()
    assert len(cases) > 1000, "corpus collapsed — the harvest is broken, not the classifier"
    mismatches = [c for c in cases if classify(*c) != explain(*c).category]
    assert mismatches == []


def test_explain_and_classify_agree_over_the_stored_offers():
    """Same assertion against real scraped rows (local only — `*.db` is gitignored).

    T1 is the CI gate; this is the pre-PR gate on data CI never sees.
    """
    db = Path(__file__).resolve().parents[1] / "grocery.db"
    if not db.exists():  # pragma: no cover - depends on the dev machine
        pytest.skip("no local grocery.db")
    rows = sqlite3.connect(db).execute(
        "SELECT name, brand, category_path, unit FROM offers"
    ).fetchall()
    if not rows:  # pragma: no cover
        pytest.skip("empty grocery.db")
    bad = [
        (n, b)
        for n, b, p, u in rows
        if classify(n, b, json.loads(p) if p else None, u)
        != explain(n, b, json.loads(p) if p else None, u).category
    ]
    assert bad == []


# --- T3/T4/T5: the counterfactual contract -------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        ("Orlando Hundetrockennahrung Rind & Gemüse", None, None, None),
        ("Radeberger Premium-Lachsschinken", None, [FOOD_ROOT, "Fisch", "Lachs"], None),
        ("Milbona Gouda gerieben XXL", None, None, "45 % Fett i.Tr. Gekühlt. 500 g"),
        ("zzz nothing matches zzz", None, None, None),
    ],
)
def test_every_layer_is_reported_in_order(case):
    """`explain` reports ALL nine layers, in order — including the ones after the winner."""
    assert [step.layer for step in explain(*case).layers] == LAYER_ORDER


def test_a_losing_layer_reports_what_it_would_have_said():
    """The counterfactual: layer 2 wins, but layer 3's path would have filed it as fish.

    This is what tells you WHERE a fix belongs — it's the difference between "the rule is
    wrong" and "the rule is right and is holding the line against a mis-filed path".
    """
    trace = explain("Radeberger Premium-Lachsschinken", None, [FOOD_ROOT, "Fisch", "Lachs"])
    assert trace.category == "pork"
    winner = trace.winner
    lachsschinken_idx = next(
        i for i, (_slug, toks) in enumerate(_FORM_OVERRIDES) if "lachsschinken" in toks
    )
    assert (winner.layer, winner.table, winner.index, winner.matched) == (
        "2", "_FORM_OVERRIDES", lachsschinken_idx, "lachsschinken",
    )
    path_layer = next(s for s in trace.layers if s.layer == "3")
    assert (path_layer.status, path_layer.slug, path_layer.matched) == ("decided", "fish", "Lachs")


def test_the_users_dog_food_case_shows_the_guard_beating_the_meat_keyword():
    """The report that started this: "Orlando in Chicken is dog food"."""
    trace = explain("Orlando Hundetrockennahrung Rind & Gemüse")
    assert trace.category == "pet"
    assert (trace.winner.layer, trace.winner.matched) == ("2", "trockennahrung")
    keywords = next(s for s in trace.layers if s.layer == "6")
    assert (keywords.slug, keywords.matched) == ("beef", "rind")


@pytest.mark.parametrize(
    "case,winning_table,next_slug",
    [
        # Empty the winning layer's table and the NEXT decided layer must take over.
        (("Radeberger Premium-Lachsschinken", None, [FOOD_ROOT, "Fisch", "Lachs"], None),
         "_FORM_OVERRIDES", "fish"),
        (("Orlando Hundetrockennahrung Rind & Gemüse", None, None, None),
         "_FORM_OVERRIDES", "beef"),
    ],
)
def test_removing_the_winning_layer_yields_the_next_decided_layer(monkeypatch, case, winning_table, next_slug):
    """The trace's promise: the next `decided` entry is what you'd get without this rule."""
    trace = explain(*case)
    assert trace.winner.table == winning_table
    monkeypatch.setattr(C, winning_table, [])
    assert classify(*case) == next_slug


# --- T6: the short-circuit that keeps classify cheap ---------------------------------


def test_classify_does_not_evaluate_layers_after_the_winner(monkeypatch):
    """`classify` must stay lazy — it runs once per scraped offer (~1650x a scrape).

    Guards against the tempting "simplification" `classify = explain(...).category`, which
    evaluates every layer instead of stopping at the winner.
    """
    calls: list[str] = []
    real = C._first_token_hit
    monkeypatch.setattr(
        C, "_first_token_hit", lambda table, hay: (calls.append("x"), real(table, hay))[1]
    )

    calls.clear()
    assert classify("Vemondo veganes Gyros", "VEMONDO") == "vegan"
    assert calls == [], "layer 0 won, so no token table should have been scanned"

    calls.clear()
    explain("Vemondo veganes Gyros", "VEMONDO")
    # L2, L5, L6 (L2b is skipped without a unit) — explain pays for the counterfactuals.
    assert len(calls) == 3

    calls.clear()
    explain("Vemondo veganes Gyros", "VEMONDO", None, "500 g")
    assert len(calls) == 4, "with a caption, layer 2b scans too"


# --- T7/T8/T9: the detail that makes a trace actionable ------------------------------


def test_layer_1_distinguishes_its_three_outcomes():
    """"household" used to be one indistinguishable answer; it's really three."""
    rescued = explain("Nektarinen 500g", None, ["Tierbedarf", "Marken für Tiere"]).winner
    assert (rescued.slug, rescued.table, rescued.matched, rescued.reason) == (
        "fruits", "_FOOD_RESCUE", "nektarine", None,
    )

    nothing = explain("PARKSIDE Akku-Bohrschrauber", None, ["Baumarkt", "Werkzeug"]).winner
    assert (nothing.slug, nothing.reason, nothing.matched) == ("household", "no_rescue_token", None)

    # A veto word killed a rescue that WOULD have matched — `blocked_slug` names it, which
    # is how you tell "the veto is earning its keep" from "no rule came near this".
    vetoed = explain("KRUPS Kaffeevollautomat", None, ["Elektronik und Technik", "Marken", "Krups"]).winner
    assert (vetoed.slug, vetoed.reason, vetoed.matched, vetoed.blocked_slug) == (
        "household", "rescue_veto", "vollautomat", "coffee",
    )


def test_layer_4_reports_which_side_the_brand_matched():
    """A "brand" hit can come from the product NAME — the trace has to say which."""
    from_column = explain("Butter", "Kerrygold").winner
    assert (from_column.slug, from_column.matched, from_column.where) == (
        "butter", "kerrygold", "brand_field",
    )
    from_name = explain("Kerrygold Butter").winner
    assert (from_name.slug, from_name.matched, from_name.where) == (
        "butter", "kerrygold", "name_text",
    )


def test_repeated_slugs_are_disambiguated_by_index():
    """`_FORM_OVERRIDES` holds "alcoholic" three times, so the slug can't name the rule."""
    hits = {
        name: explain(name).winner
        for name in ("Benediktiner Hell oder alkoholfrei", "Weinschorle 0,5l", "Jägermeister 0,7l")
    }
    assert all(h.slug == "alcoholic" and h.table == "_FORM_OVERRIDES" for h in hits.values())
    # The POINT is that one slug maps to three DISTINCT rules, so the index is what names a
    # rule. Derived rather than hardcoded: absolute positions shift whenever an entry is
    # inserted above, which made this fail for a reason that had nothing to do with its claim.
    indices = [h.index for h in hits.values()]
    assert len(set(indices)) == 3, "three alcoholic entries must be three distinct rules"
    for name, h in hits.items():
        assert h.matched in _FORM_OVERRIDES[h.index][1], name
        assert _FORM_OVERRIDES[h.index][0] == "alcoholic", name


def test_skipped_layers_say_why_they_could_not_run():
    """"Skipped" and "nothing matched" are different answers and must not be conflated."""
    no_path = {s.layer: s for s in explain("Butter", None, None, "250 g").layers}
    assert (no_path["1"].status, no_path["1"].reason) == ("skipped", "no_category_path")
    assert (no_path["3"].status, no_path["3"].reason) == ("skipped", "no_category_path")

    no_unit = {s.layer: s for s in explain("Butter", None, [FOOD_ROOT, "Molkereiprodukte"]).layers}
    assert (no_unit["2b"].status, no_unit["2b"].reason) == ("skipped", "no_unit")
    assert (no_unit["1"].status, no_unit["1"].reason) == ("skipped", "path_is_food_root")

    # An empty caption stays skipped — `if unit:`, not `is not None`.
    assert explain("Butter", None, None, "").layers[3].reason == "no_unit"


# --- T10/T11: the inputs the API otherwise hides -------------------------------------


def test_inputs_expose_the_category_path_and_the_real_padded_haystacks():
    """`category_path` is invisible in OfferOut, and the padding explains the space guards."""
    path = [FOOD_ROOT, "Fisch"]
    trace = explain("Lachs", "Followfish", path, "200 g")
    assert trace.inputs.category_path == path
    assert trace.inputs.text == " lachs followfish "  # padded, lowercased — verbatim
    assert trace.inputs.caption == " 200 g "
    assert explain("Lachs").inputs.caption is None


def test_vegan_match_reports_the_literal_and_is_vegan_still_returns_a_bool():
    """`is_vegan` must keep its contract — returning the matched string would be truthy too."""
    # Original casing preserved, and the match stops at "Vegan" — `_VEGAN_RE` guards its LEFT
    # boundary only (so it fires on vegane/veganes) and has no right boundary.
    assert vegan_match("Rügenwalder Vegane Mühlen BBQ-Filets") == "Vegan"
    assert vegan_match("Butter") is None
    assert is_vegan("Oatly Haferdrink") is True
    assert is_vegan("Butter") is False


# --- the post-layer preserved-produce redirect (2026-08-15) ---------------------------

# The real stored row: `_PATH_MAP["Wurzelgemüse"]` decides `vegetables` at layer 3, and the
# caption is what says it is a jar. An invented path would prove nothing here — the whole
# point is which layer a REAL path routes through.
_JAR = ("ALL SEASONS Schwarzwurzeln", "ALL SEASONS",
        ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Gemüse", "Wurzelgemüse",
         "Schwarzwurzeln"],
        "Abtropfgewicht (ATG) = 320 g 580-ml-Glas")


def test_explain_reports_the_redirect_and_the_answer_it_overrode():
    """A trace whose category no layer produced is a trace that lies about itself.

    So the redirect is reported as its own entry, and it names what it displaced — otherwise
    the reader sees "pantry" over a layer list whose only decided line says "vegetables" and
    has to guess. `layers` deliberately stays exactly LAYER_ORDER; the override rides beside
    it, not inside it.
    """
    tr = explain(*_JAR)
    assert tr.category == "pantry"
    assert tr.redirect is not None
    assert tr.redirect.table == "_PRESERVED_CAPTION"
    assert tr.redirect.matched == "abtropfgewicht"
    assert tr.redirect.blocked_slug == "vegetables", "must name the answer it overrode"
    assert tr.winner is tr.redirect, "`winner` is what produced `category`"
    # The layer walk is untouched and still reports what it really found.
    assert [s.layer for s in tr.layers] == LAYER_ORDER
    first = next(s for s in tr.layers if s.status == "decided")
    assert (first.slug, first.table) == ("vegetables", "_PATH_MAP")


def test_a_trace_without_a_redirect_says_so():
    """The negative case, so `redirect` can't just be always-set."""
    tr = explain("REWE Bio Staudensellerie", "REWE Bio",
                 ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Gemüse"],
                 "Deutschland Kl. II")
    assert tr.category == "vegetables"
    assert tr.redirect is None
    assert tr.winner is _winner_of(tr)


def _winner_of(tr):
    return next(s for s in tr.layers if s.status == "decided")


def test_the_redirect_costs_classify_no_extra_table_scan(monkeypatch):
    """The redirect must not de-lazify `classify`, which runs once per scraped offer.

    `_redirect` reads five substrings off a short caption and scans no rule table, so the
    count is whatever the layer walk already cost. A `tuple(layers)` slipped into `_decide`
    — or a rewrite of the redirect as a terminal layer, which would have to exhaust the
    generator to be reached — shows up here immediately.
    """
    calls: list[str] = []
    real = C._first_token_hit
    monkeypatch.setattr(
        C, "_first_token_hit", lambda table, hay: (calls.append("x"), real(table, hay))[1]
    )
    calls.clear()
    assert classify(*_JAR) == "pantry"
    lazy = len(calls)
    calls.clear()
    explain(*_JAR)
    eager = len(calls)
    assert lazy < eager, (
        f"classify must stop at the winner ({lazy} scans) while explain pays for every "
        f"counterfactual ({eager}) — equal counts mean the redirect de-lazified classify"
    )
