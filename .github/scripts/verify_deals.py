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
  * per-chain floor >= 100, ENFORCED ONLY WITH --post-reset — a chain that is present but
    nearly empty. `chains` above counts presence with no cardinality behind it, so one
    surviving offer is indistinguishable from a full brochure, and the total-offers floor
    is easily carried by the healthy chains: at the measured 2026-08-02 counts (aldi 247,
    edeka 234, edeka_center 274, lidl 417, rewe 390 = 1562), THREE of the five could fall
    back to sample data and still clear 800 (1562-247-234-274+4+5+5 = 821). Drugstore is
    blind to a dark dm outright, and catches a dark Rossmann only by luck — it depends on
    dm's clearance list, which swings week to week.

    Only gated with --post-reset because a chain legitimately empties between brochures:
    Rossmann's week ends Friday, so on a Saturday it really does serve ~2 offers. Right
    after the weekly wipe-and-re-scrape, though, every chain is supposed to have a fresh
    brochure, so a thin one there is an incident. The breakdown prints either way.

    An ABSENT chain can never appear here (it has no key to count), so the failure space
    partitions cleanly: absent -> the `chains` check, present-but-thin -> this one, never
    both. That is why this check cannot print a 0 — a property, not a gap.

Usage:
  verify_deals.py --url https://…/api/offers --plz 10115   # live (the weekly workflow)
  verify_deals.py --url … --post-reset                     # …right after /api/reset
  verify_deals.py --file fixture.json                      # offline (prove it fails)

Exit 0 = healthy; exit 1 = a floor was violated (the workflow's existing failure alerting
takes over). Prints counts only — never the PLZ, which can be a secret. Note that store
NAMES embed it (`bonial.py` builds f"{store_label} {plz}"), so everything printed here is
keyed on `chain`; never reach for `store_name`.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

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
# What /api/offers caps at. A response of exactly this length was TRUNCATED, and truncation
# happens after a sort by discount_pct with None last — which is disproportionately REWE and
# ALDI, i.e. exactly the chains nearest the per-chain floor. So a capped response would make
# this whole report lie, and the per-chain check lie first. Fail instead of guessing.
SERVE_LIMIT = 2000

# `min_chain_offers` is calibrated on SUNDAY POST-RESET counts — the only regime this gate
# runs in, and not the same as "offers valid on an arbitrary weekday": /api/offers filters on
# `valid_to >= today` ALONE, with no `valid_from <=` clause, so a chain's day-limited windows
# (ALDI ships 146 Mon–Sat + 90 Thu–Sat + 7 Sat) are all served from day one. Measuring with a
# valid_from clause reads ALDI as 150 instead of its real 247 and would set the floor far too
# high. Five Sunday runs, from the stored offers:
#
#     chain          07-05  07-12  07-19  07-26  08-02
#     aldi               -      -      4    287    247
#     edeka            253    252    234    234    234
#     edeka_center     304    272    280    278    274
#     lidl             361    452     38    395    417
#     rewe             378    405      5    434    390
#     rossmann           -      -      -      -    289
#     dm                 -      -      -      -    213
#
# Healthy minimum 213 (dm), then 234 (edeka, three Sundays running). Failure population:
# 2, 4, 5, 5, 6, 38 — the 38 is Lidl during the 2026-07-19 throttle incident, a PARTIAL PARSE
# rather than a sample fallback (its sample is 4), so it sets the lower bound. 100 sits 2.6x
# above the worst observed failure and 2.1x below the worst observed health, matching this
# file's own house factor (offers 800 against a measured 1650 is 0.48x; 100/213 is 0.47x).
# 50 would be only 1.3x above that Lidl-38 and would pass a partial parse at 60.
#
# The binding constraint is dm (n=1, and its clearance list is documented as volatile), NOT
# ALDI. Raise toward 150 only after ~8 more Sundays with no chain under ~210 and dm observed
# >=6 times; if a healthy week ever lands in the 100-160 band, prefer a per-chain override
# over lowering the global number, which would weaken ALDI/Lidl/REWE protection for free.
PROFILES: dict[str, dict] = {
    # Measured 2026-07-15, prod AND local agreeing: 1650-1663 offers, 5 chains, ~71% €/kg,
    # ~7.4% "other". Unchanged by the split — this is still the same population.
    "grocery": {"chains": 5, "offers": 800, "unit_price_pct": 50.0, "other_pct": 15.0,
                "min_chain_offers": 100},
    # Measured 2026-07-30: Rossmann 283 + dm 214 = ~497.
    #
    # `chains` is the load-bearing check here, NOT the offer floor. dm's feed is a
    # clearance list whose size genuinely swings week to week (one observation so far),
    # so a tight offers floor would flap on healthy weeks; but if either chain falls back
    # to samples or stops parsing, the chain count drops to 1 and that is unambiguous.
    # The offers floor stays deliberately loose — it only has to catch a total collapse.
    #
    # …except it does NOT drop to 1 when the chain merely goes thin, which is what happened on
    # 2026-08-08 (rossmann 2 vs 287 the week before). `min_chain_offers` is the check that
    # actually names the chain; the offers floor caught that one only because dm happened to
    # be at 213 that week, and would have passed it at dm's own measured 250.
    "drugstore": {"chains": 2, "offers": 250, "unit_price_pct": None, "other_pct": 15.0,
                  "min_chain_offers": 100},
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
    params = {"plz": plz, "limit": SERVE_LIMIT}
    if vertical:
        params["vertical"] = vertical
    qs = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{qs}", timeout=180) as resp:
        return json.load(resp)


def verify(offers: list[dict], profile: dict, *, post_reset: bool = False) -> int:
    """Judge one vertical's served offers. `post_reset` says a wipe-and-re-scrape just ran, so
    every chain should carry a fresh brochure — it is what arms the per-chain floor.

    Keyword-only and defaulting to False on purpose: a caller that forgets it gets the LENIENT
    behaviour, never a surprise red.
    """
    chains = sorted({o.get("chain") for o in offers if o.get("chain")})
    total = len(offers)
    # Keyed on `chain`, never `store_name` — store names embed the PLZ (see the module docstring).
    per_chain = Counter(o["chain"] for o in offers if o.get("chain"))
    # A plain subscript, NOT .get(..., 0): a default would silently disable this check for a
    # future profile that forgot the key, while a KeyError exits non-zero, which fails closed.
    floor_chain = profile["min_chain_offers"]
    thin = sorted(c for c, n in per_chain.items() if n < floor_chain)
    if thin:
        chain_verdict = "thin: " + ", ".join(f"{c}={per_chain[c]}" for c in thin)
    elif per_chain:
        chain_verdict = f"min {min(per_chain.values())}"
    else:
        chain_verdict = "no chains"  # already failing `chains` and `offers` twice over
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
        # Directly after `chains`, and BEFORE `offers`: the two are one question read top to
        # bottom ("is every chain present, and is every present chain alive"). Below the offers
        # line the reader hits "offers: 208 (floor 250)" first and stops at the wrong diagnosis
        # — which is exactly what the 2026-08-08 dark-Rossmann run did.
        (not post_reset or not thin,
         f"per-chain floor: {chain_verdict} (floor {floor_chain})"
         + ("" if post_reset else "  [not gated: --post-reset not set]")),
        # A response of exactly the cap was truncated, so every count above is a floor, not a
        # count — including the per-chain ones. Fail rather than report numbers we can't trust.
        (total < SERVE_LIMIT,
         f"not truncated: {total} (serve cap {SERVE_LIMIT})"),
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
    # The per-chain histogram prints ALWAYS, pass or fail. It is the only record of what a
    # healthy week looked like, and recalibrating the floor after an incident needs the runs
    # from BEFORE it — this data otherwise has to be reconstructed from a SQLite file.
    if per_chain:
        print("        " + "  ".join(f"{c} {n}" for c, n in sorted(per_chain.items())))
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
    ap.add_argument("--post-reset", action="store_true",
                    help="a wipe-and-re-scrape just ran, so every chain should carry a fresh "
                         "brochure — enforces the per-chain floor (the weekly workflow sets this)")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            offers = json.load(f)
        if not isinstance(offers, list):
            print(f"FAIL  response is not an offer list ({type(offers).__name__})")
            return 1
        return verify(offers, PROFILES[args.vertical or "grocery"],
                      post_reset=args.post_reset)

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
        failed = verify(offers, profile, post_reset=args.post_reset) != 0 or failed
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
