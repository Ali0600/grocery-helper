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

FLOOR_CHAINS = 5
FLOOR_OFFERS = 800
FLOOR_UNIT_PRICE_PCT = 50.0
CEIL_OTHER_PCT = 15.0


def fetch(url: str, plz: str) -> list[dict]:
    qs = urllib.parse.urlencode({"plz": plz, "limit": 2000})
    with urllib.request.urlopen(f"{url}?{qs}", timeout=180) as resp:
        return json.load(resp)


def verify(offers: list[dict]) -> int:
    chains = sorted({o.get("chain") for o in offers if o.get("chain")})
    total = len(offers)
    with_unit = sum(1 for o in offers if o.get("unit_price_cents"))
    other = sum(1 for o in offers if o.get("category") == "other")
    unit_pct = (with_unit / total * 100) if total else 0.0
    other_pct = (other / total * 100) if total else 0.0

    checks = [
        (len(chains) >= FLOOR_CHAINS,
         f"chains: {len(chains)} {chains} (floor {FLOOR_CHAINS})"),
        (total >= FLOOR_OFFERS,
         f"offers: {total} (floor {FLOOR_OFFERS})"),
        (unit_pct >= FLOOR_UNIT_PRICE_PCT,
         f"eur/kg sortable: {unit_pct:.1f}% (floor {FLOOR_UNIT_PRICE_PCT}%)"),
        (other_pct <= CEIL_OTHER_PCT,
         f"'other' rate: {other_pct:.1f}% (ceiling {CEIL_OTHER_PCT}%)"),
    ]
    failed = False
    for ok, line in checks:
        print(("PASS  " if ok else "FAIL  ") + line)
        failed = failed or not ok
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="offers endpoint, e.g. https://host/api/offers")
    ap.add_argument("--plz", default="10115")
    ap.add_argument("--file", help="offline: verify a saved offers JSON instead")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            offers = json.load(f)
    elif args.url:
        offers = fetch(args.url, args.plz)
    else:
        ap.error("need --url or --file")
        return 2
    if not isinstance(offers, list):
        print(f"FAIL  response is not an offer list ({type(offers).__name__})")
        return 1
    return verify(offers)


if __name__ == "__main__":
    sys.exit(main())
