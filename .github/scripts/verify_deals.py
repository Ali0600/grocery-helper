#!/usr/bin/env python3
"""Data-quality gate over the served deals — "one report = audit the whole class",
running on a schedule instead of waiting for a human to notice something odd.

Asserts, against measured norms (2026-07-15, prod AND local agreeing: 1650-1663 offers,
5 chains, ~71% with a €/kg, ~7.4% "other" — calibrating this gate corrected an earlier
~1% belief that came from a different week's survey), with conservative floors so normal
weekly variance never flaps. This is a smoke alarm for collapse, not a quality aspiration:

  * distinct chains >= 5   — a missing chain IS an incident, even when the skip was a
    designed degradation (ALDI's fail-closed Nord/Süd routing): fail-closed must announce
    itself, and this is the announcement. The alert issue auto-closes on recovery.
  * total offers >= 800    — a half-empty week means scrapers fell back to samples.
  * €/kg-sortable >= 50%  — a collapse here means the feed's Grundpreis shape drifted
    past the parser again (the family of bugs that produced normalize_price_per_unit).
  * "other" rate <= 15%   — roughly 2x the measured norm; a taxonomy break sends this
    far higher, while weekly brand-mix variance stays well under it.
  * self-disagreement <= 20% OF COMPARABLE PRODUCTS — the same product NAME served in two
    different categories. Free to compute and needs no ground truth: the classifier
    contradicting itself means at least one of those rows is wrong by construction, so a jump
    here is a taxonomy break even when every other number looks healthy.

    The denominator is load-bearing and is NOT the served total. The served set is deduped, so
    only ~16% of offers share a name with any other offer (126 of 1500 names, 2026-07-17) —
    every unique name is unjudgeable by this check. Expressed against the served total the rate
    is ~2%, and a "2x the norm" ceiling of 4% would need a QUARTER of all comparable products
    to disagree before tripping: a gate that reads authoritative while evaluating almost
    nothing. Measured against comparable products it is 11.9% live (15 of 126), so the ceiling
    is 20% — and a scrambled-category fixture trips it, which the served-total form did not.

    Deliberately NOT zero: some disagreements are legitimate — the source files the
    alcohol-free Heineken under "Getränke > Alkoholfreie Getränke" and the regular one under
    "Bier > Biermarken", so that one name honestly spans two categories.

Usage:
  verify_deals.py --url https://…/api/offers --plz 10115   # live (the weekly workflow)
  verify_deals.py --file fixture.json                      # offline (prove it fails)

Exit 0 = healthy; exit 1 = a floor was violated (the workflow's existing failure alerting
takes over). Prints counts only — never the PLZ, which can be a secret.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

CEIL_SELF_DISAGREE_PCT = 20.0
# Below this many comparable products the rate is too noisy to gate on (one disagreement in a
# handful of names would swing it past any ceiling). Grocery carries ~126; drugstore, at one
# chain and ~283 offers, will usually fall under it and skip — which is the honest answer.
MIN_COMPARABLE = 20

# One profile per vertical, because a single global gate would be wrong in both directions:
# `chains >= 5` goes RED the moment the served set is vertical-scoped, and a floor loose
# enough for a one-chain drugstore could not detect a grocery collapse. Each vertical is
# fetched and judged separately.
#
# `unit_price_pct: None` means "don't gate on it". Measured 2026-07-30, Rossmann carries a
# Grundpreis on **48%** of offers — under grocery's 50% floor — and €/kg is barely meaningful
# for cosmetics anyway, so gating it there would be a permanent red with nothing behind it.
PROFILES: dict[str, dict] = {
    # Measured 2026-07-15, prod AND local agreeing: 1650-1663 offers, 5 chains, ~71% €/kg,
    # ~7.4% "other". Unchanged by the split — this is still the same population.
    "grocery": {"chains": 5, "offers": 800, "unit_price_pct": 50.0, "other_pct": 15.0},
    # Measured 2026-07-30: Rossmann 283 + dm 214 = ~497.
    #
    # `chains` is the load-bearing check here, NOT the offer floor. dm's feed is a
    # clearance list whose size genuinely swings week to week (one observation so far),
    # so a tight offers floor would flap on healthy weeks; but if either chain falls back
    # to samples or stops parsing, the chain count drops to 1 and that is unambiguous.
    # The offers floor stays deliberately loose — it only has to catch a total collapse.
    "drugstore": {"chains": 2, "offers": 250, "unit_price_pct": None, "other_pct": 15.0},
}


def self_disagreeing(offers: list[dict]) -> tuple[list[tuple[str, set[str], int]], int]:
    """(disagreeing products, comparable count).

    "Comparable" = names served at least twice: a name served once cannot disagree with
    anything, so it belongs in neither the numerator nor the denominator.
    """
    cats: dict[str, set[str]] = defaultdict(set)
    seen: dict[str, int] = defaultdict(int)
    for o in offers:
        name = (o.get("name") or "").strip().lower()
        cat = o.get("category")
        if not name or not cat:
            continue
        cats[name].add(cat)
        seen[name] += 1
    comparable = [n for n, c in seen.items() if c > 1]
    bad = [(n, cats[n], seen[n]) for n in comparable if len(cats[n]) > 1]
    return bad, len(comparable)


def fetch(url: str, plz: str, vertical: str | None = None) -> list[dict]:
    params = {"plz": plz, "limit": 2000}
    if vertical:
        params["vertical"] = vertical
    qs = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{qs}", timeout=180) as resp:
        return json.load(resp)


def verify(offers: list[dict], profile: dict) -> int:
    chains = sorted({o.get("chain") for o in offers if o.get("chain")})
    total = len(offers)
    with_unit = sum(1 for o in offers if o.get("unit_price_cents"))
    other = sum(1 for o in offers if o.get("category") == "other")
    unit_pct = (with_unit / total * 100) if total else 0.0
    other_pct = (other / total * 100) if total else 0.0
    disagree, comparable = self_disagreeing(offers)
    disagree_pct = (len(disagree) / comparable * 100) if comparable else 0.0
    floor_unit = profile["unit_price_pct"]

    checks = [
        (len(chains) >= profile["chains"],
         f"chains: {len(chains)} {chains} (floor {profile['chains']})"),
        (total >= profile["offers"],
         f"offers: {total} (floor {profile['offers']})"),
        (floor_unit is None or unit_pct >= floor_unit,
         f"eur/kg sortable: {unit_pct:.1f}% "
         + (f"(floor {floor_unit}%)" if floor_unit is not None else "(not gated here)")),
        (other_pct <= profile["other_pct"],
         f"'other' rate: {other_pct:.1f}% (ceiling {profile['other_pct']}%)"),
        # Skipped rather than passed when there's nothing to compare: "couldn't evaluate" must
        # not read as "all clear" (it still fails the offers floor above if the set collapsed).
        (comparable < MIN_COMPARABLE or disagree_pct <= CEIL_SELF_DISAGREE_PCT,
         f"self-disagreeing: {disagree_pct:.1f}% of comparable "
         f"({len(disagree)} of {comparable} products served >=2x, "
         f"ceiling {CEIL_SELF_DISAGREE_PCT}%)"
         + ("  [SKIPPED: too few comparable products]" if comparable < MIN_COMPARABLE else "")),
    ]
    failed = False
    for ok, line in checks:
        print(("PASS  " if ok else "FAIL  ") + line)
        failed = failed or not ok
    # Name the offenders on failure — the count alone can't be acted on. Names are product
    # names from a public flyer, so this prints nothing personal (cf. the PLZ rule above).
    if comparable >= MIN_COMPARABLE and disagree_pct > CEIL_SELF_DISAGREE_PCT:
        for name, cat_set, n in sorted(disagree, key=lambda d: -d[2])[:15]:
            print(f"        {n}x  {','.join(sorted(cat_set))}  {name[:56]}")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="offers endpoint, e.g. https://host/api/offers")
    ap.add_argument("--plz", default="10115")
    ap.add_argument("--file", help="offline: verify a saved offers JSON instead")
    ap.add_argument("--vertical", choices=sorted(PROFILES),
                    help="offline: which profile to judge --file against (default grocery)")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            offers = json.load(f)
        if not isinstance(offers, list):
            print(f"FAIL  response is not an offer list ({type(offers).__name__})")
            return 1
        return verify(offers, PROFILES[args.vertical or "grocery"])

    if not args.url:
        ap.error("need --url or --file")
        return 2

    # Every vertical is judged on its OWN thresholds, and every one runs even after a
    # failure — a red grocery must not hide a collapsed drugstore.
    failed = False
    for vertical, profile in PROFILES.items():
        print(f"--- {vertical} ---")
        offers = fetch(args.url, args.plz, vertical)
        if not isinstance(offers, list):
            print(f"FAIL  response is not an offer list ({type(offers).__name__})")
            failed = True
            continue
        failed = verify(offers, profile) != 0 or failed
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
