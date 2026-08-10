# Decision log — the roads not taken

When a design fork gets decided, the **rejected** options hold most of the thinking: the
tradeoff that made the call close, and often a "worth trying later". That evaporates the moment
we move on. This file keeps it.

Each entry: the fork, every option with its tradeoff, what was chosen and why, a **status** per
rejected option, and a **revisit hook** — the concrete seam where trying it later would plug in.

Skip trivial forks (a name, a colour, a one-line default). This is for decisions with real
alternatives.

> Started 2026-08-09 and backfilled from that session plus the one before it. Earlier decisions
> live in `CLAUDE.md`'s notes and in PR bodies; they were not retro-fitted here.

---

## Backlog — alternatives worth trying later

The one-glance menu. Only `deferred` items appear here.

- **Serve-time `valid_from <= today` filter on `/api/offers`** — would stop a Sunday-scraped
  flyer being browsable a day before it starts. Deliberately not done; see *Restored offers
  serve a day early*.
- **A brochure "age" guard as a second signal** — an active brochure that started more than a
  week ago is probably not this week's flyer. Would have caught the Rossmann case independently
  of the imminence window; see *How to stop a stale supplement shadowing the weekly flyer*.
- **A `{"default": 100, "dm": 60}` per-chain override map in the data gate** — only worth it if
  a healthy week ever lands in the 100–160 band; see *Per-chain floor: one number or per-chain*.

---

## 2026-08-09 — How to stop a stale supplement shadowing the weekly flyer

Rossmann served **2 offers of 302** because `_select_brochures` early-returned on any *active*
brochure, and a 6-page, 11-day supplement was active while the real 26-page weekly started that
evening. The fork was how to express "this is the current edition", given that validity alone
cannot.

| Option | Tradeoff |
|---|---|
| **A. Union active + "starts today or tomorrow (Berlin)"** | Encodes the real publishing calendar. Needs a second, tighter window than the existing lookahead. |
| B. Tighten `MAX_FLYER_DAYS` below 11 days | One-line change, but **span is the wrong discriminator** — it would also drop legitimate 11-day brochures, and a 15-day supplement would still slip through. |
| C. An "age" guard: an active brochure that started >7 days ago cannot suppress the upcoming branch | Also correct here, and orthogonal to A. Needs a threshold picked from data we do not have much of. |
| D. Reuse `UPCOMING_LOOKAHEAD_DAYS` (8 days) for the union | No new constant — but it pulls in the *following* week mid-week (Lidl already lists its next-next flyer 7 days out). |
| E. Pick the brochure with the most pages | Tempting, and wrong: page count is not a contract, and a legitimately small weekly would lose. |

**Chose A.** The window is expressed in Berlin calendar days rather than hours because every
boundary in this feed is a Berlin midnight, so an hour count drifts across DST. Its safety is
*provable* from the calendar rather than tuned: a weekly ends Sat ~23:00 Berlin and the next
starts Mon 00:00, so while one is active "today or tomorrow" reaches at most Sunday — the two
sets can never overlap.

- B — **rejected**: span does not discriminate; it is what already failed.
- C — **deferred — worth trying** as a *second* signal if a case appears that A misses (e.g. a
  supplement running while the weekly is genuinely absent).
- D — **rejected**: measured to leak next week's prices mid-week.
- E — **rejected**: no contract behind it.

**Revisit hook:** `_starts_within_a_day()` and `_select_brochures()` in
`backend/app/scrapers/bonial.py`. C would slot in as an extra filter on the `active` list, right
where it is built.

---

## 2026-08-09 — Restored offers serve a day early

Fixing Rossmann restored 300 offers whose `valid_from` is the following Monday, and
`/api/offers` filters `valid_to >= today` with **no `valid_from` clause** — so they became
browsable on Sunday.

| Option | Tradeoff |
|---|---|
| **A. Leave it** | Consistent: every grocery chain's Sunday-scraped flyer already behaves this way, and the weekly reset exists precisely to load the coming week. |
| B. Add `valid_from <= today` to the serve filter | Strictly more correct about "on sale now" — but it would also hide **day-limited** deals (a Thu–Sat special) for most of the week, which the app deliberately shows with an orange day pill. |

**Chose A**, as the smaller and more consistent change; B was out of scope for a scraper fix.

- B — **deferred — worth trying**, but only together with a decision about day-limited offers,
  since it changes them too. It is not a pure win.

**Revisit hook:** the validity filter in `backend/app/api/offers.py`, and `valid_days` /
`day_limited` in `backend/app/validity.py`.

---

## 2026-08-09 — Naming a rule narrowly vs guarding a broad one

A candidate `président` → cheese would have filed **"Corsaire Réserve du Président"**, a French
dry wine, as cheese. The wine has no category path, so nothing above layer 6 protects it.

| Option | Tradeoff |
|---|---|
| **A. Narrow the token to `président carré`** | Fixes the one product it was written for; buys no coverage of future Président cheeses. |
| B. Keep bare `président`, add a guard entry above it for the wine | The project's established idiom for a broad-token-with-nameable-exceptions (`bananen` shipped this way). Broader coverage, one more rule to maintain, and the exception list grows with every wine that borrows the word. |
| C. Drop it; leave the product in `other` | Honest, but `other` renders in the food list. |

**Chose A.** "Président" is a *word*, not a product kind — Réserve du Président, Cuvée du
Président — so the exception list under B is open-ended in a way `bananen`'s was not.

- B — **rejected**: the false positives are not enumerable, which is the project's own bar for
  shipping a broad token.
- C — **rejected**: leaves a cheese unclassified for no gain.

**Revisit hook:** the `cheese` tuple in `_RULES`, `backend/app/categories.py`. If Président
cheeses start appearing under other names, B becomes the better shape.

---

## 2026-08-09 — Photo sweep before or after the Rossmann fix

The user asked for the full sweep in the same session as the outage fix.

| Option | Tradeoff |
|---|---|
| **A. Fix and deploy Rossmann first, then sweep** | Sheets cover the restored 302 products, and the drugstore vertical is not 63% one chain's clothing clear-out. Costs a deploy wait. |
| B. Sweep immediately, in parallel | Faster wall-clock, but samples a dataset about to change by 300 products and re-finds what the pending classifier PR already fixes. |

**Chose A**, and additionally computed each product's *post-PR* category locally so the sheets
never showed an answer that was already fixed.

- B — **rejected — measurement-ordering**, not a preference: the sweep's whole value is judging
  the answer the user will actually see.

---

## 2026-08-08 — Per-chain floor: one number or per-chain

`chains >= N` counts *presence*, so a chain serving 2 offers read as healthy. The fork was how
to add cardinality without the gate flapping during a chain's normal publishing gap.

| Option | Tradeoff |
|---|---|
| **A. One floor (100) for every chain, armed only by `--post-reset`** | Simple, one number to calibrate. Right after a wipe-and-re-scrape every chain should be full, so a thin one is an incident. |
| B. Per-chain floors derived from each chain's measured history | Tighter, but five numbers to maintain and only one Sunday of data for dm and Rossmann. |
| C. Percentage-of-total floor | Self-scaling — but it moves when *other* chains move, so one collapsed chain raises the bar for the rest. |
| D. Always-on, not gated on `--post-reset` | Catches more, and would have gone red every Saturday when Rossmann's week legitimately ends. Training the user to ignore the alarm is worse than the miss. |

**Chose A.** 100 sits 2.6× above the worst observed failure (Lidl's 38-offer partial parse) and
2.1× below the worst observed health (dm's 213).

- B — **deferred — worth trying** once there are ~8 more Sundays of the per-chain histogram the
  gate now prints on every run.
- C — **rejected**: the coupling is backwards.
- D — **rejected**: flapping on a designed degradation.

**Revisit hook:** `PROFILES` in `.github/scripts/verify_deals.py`. If a healthy week ever lands
in the 100–160 band, prefer a `{"default": 100, "dm": 60}` override map over lowering the global
number, which would weaken ALDI/Lidl/REWE protection for free.
