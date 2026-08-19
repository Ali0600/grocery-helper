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
- **Raise the `/api/offers` serve cap (2000) so Netto and Kaufland become addable** — both
  measured over it; see *Which chain becomes the sixth, and the cap it runs into*.
- **A `{"default": 100, "dm": 60}` per-chain override map in the data gate** — only worth it if
  a healthy week ever lands in the 100–160 band; see *Per-chain floor: one number or per-chain*.
- **Move Coffee into the Drinks section** — kept in Grocery by the user's call; a one-line
  change to `DRINK_CATEGORIES` if Drinks ever feels thin. See *Where a "Drinks" section lives*.
- **Prune the History entry when a basket add is undone** — History is append-only today, so a
  mis-tap leaves a row behind; see *What happens when you press the Basket button a second time*.

---

## 2026-08-18 — Where a "Drinks" section lives, and what it takes with it

The user asked for drinks out of the grocery list ("I'm just looking for food and it's
distracting") and for a Drinks button on the home screen. Measured that day: grocery served
**1,926 of the 2,000 cap** and drinks were **237** of it, so this was also the cheapest
headroom available.

### Fork 1 — where the split happens

| option | tradeoff |
| --- | --- |
| **A backend vertical scoped by CATEGORY** (chosen) | Needs a second shape of `VerticalSpec` and a partition invariant between two entries. Buys real cap headroom (grocery 1,926 → 1,689), and every existing contract — one `vertical` param, one cache key per section, one gate profile — keeps its shape instead of growing an exception. |
| A client-side filter over one grocery fetch | No backend change and no deploy ordering. But the 1,926-row query stays at 96% of the cap, i.e. it fixes the *complaint* and not the *problem* underneath it, and every count the app derives (chips, facets, Compare) would need its own drinks-aware branch. |
| A `?exclude_category=` query param | More general, and generality is the trap: the app would then own the definition of "what is a drink", in a query string, with no server-side invariant tying grocery's exclusion to drinks' inclusion. |
| Drinks as a fourth *chain set* (a drinks retailer) | Not the request, and there is no such flyer source. |

**Chosen: A.** Status of the rejected: client-side filter — `rejected — leaves the cap
problem`; `exclude_category` — `rejected — moves the partition to the client, where nothing
can enforce it`; drinks retailer — `rejected — no source`.

**Revisit hook:** `backend/app/verticals.py`. A second category carve-out is now a
`VerticalSpec(categories=…)` entry plus the matching `excluded_categories` on its home
section; `tests/test_verticals.py` checks the agreement generically, so nothing new is needed
to make it safe.

### Fork 2 — does Coffee go with the drinks?

Coffee is 42 offers and was split out of `soft_drinks` in July for the same "a bag of beans
is not a soft drink" reason. **The user chose to keep it in Grocery** — it is an aisle you
cook from. Status: `deferred — worth trying` if the Drinks section ever feels thin; it is a
one-line change to `DRINK_CATEGORIES`, and a test pins the current answer so the move has to
be deliberate.

**Revisit hook:** `DRINK_CATEGORIES` in `backend/app/verticals.py`, plus the assertion in
`test_drinks_is_the_grocery_chains_and_nothing_else`.

### Fork 3 — is the Basket scoped to the section you are standing in?

| option | tradeoff |
| --- | --- |
| **Merged across Grocery + Drinks** (chosen, the user's call) | The two sections are the same six supermarkets and one shopping trip, so a beer belongs on the same list as the bread. Costs a companion-cache read in `DealsScreen` and a rule about when it may be fetched. |
| Scoped, exactly like Drugstore | Zero new mechanism, consistent with the existing section boundary. But a basket that says "No deal this week" for a beer that *is* on sale two taps away is wrong in the way the user would actually notice. |

Status of the rejected option: `rejected — the sections are one shopping trip`. Note this is
where Drinks stops resembling Drugstore: the drugstore chains are a different errand, so
merging *that* would be wrong for the same reason merging this is right.

**Revisit hook:** `companionVertical()` in `mobile/src/verticals.ts` — it returns `null` for
Drugstore, which is the whole statement.

## 2026-08-11 — Which chain becomes the sixth, and the cap it runs into

Netto, Penny and Kaufland all sat in the store directory as "Deals coming soon". Probed live
(Berlin cookie, paced) on 2026-08-11 — all three publish a normal weekly on meinprospekt:

| candidate | publisher | raw products | grocery total | vs the 2000 serve cap |
|---|---|---|---|---|
| **Penny** | `DE-1050` `/penny-de` | 313 (255 deduped) | ~1930 | **under** |
| Netto Marken-Discount | `DE-1034` | 461 | ~2070 | over |
| Kaufland | `DE-424316869` | 723 | ~2280 | over |

| Option | Tradeoff |
|---|---|
| **A. Penny now; Netto/Kaufland behind a cap decision** | Ships a whole chain with no cap work. Penny is REGIONAL (Berlin `2501215484` vs Munich `2501215489`), so the existing cookie pinning is what makes it correct — the well-trodden REWE/EDEKA path. |
| B. Netto first | The everyday Berlin discounter and the bigger content win, but it crosses the cap, and `store_locator` prefix-matches **two** unrelated Nettos (`DE-1034` Marken-Discount and `DE-1122` "mit dem Scottie") into one slug. Two problems in one PR. |
| C. Kaufland first | Biggest content win (723), clearly over the cap, and its brochures run overlapping mid-week windows (08-05→08-12 *and* 08-09→08-12) that `_select_brochures` has never been exercised against. |
| D. Add a server-side `q` search param instead of raising the cap | Does **not** solve it. Search is only one of ~12 passes over the loaded array — category chip counts, `presentChains`, facet counts, Basket matching, Compare and Recipes all read the same list, so a truncated browse list makes all of them quietly wrong. |
| E. Raise the cap to ~3000 | The actual fix when it is needed. Deferred only because Penny does not need it. |

**Chose A.** Truncation is the reason the cap matters at all: `/api/offers` slices *after* a
discount sort with nulls last, and REWE/EDEKA/E center/ALDI mostly publish no strike price — so
the rows dropped at the cap are disproportionately those chains. Shipping a chain that crosses it
would silently corrupt the very comparisons the app exists for.

- B, C — **deferred — worth trying**, both gated on E.
- D — **rejected**: measured to fix the wrong surface.
- E — **deferred — worth trying**, and it is the prerequisite for B and C.

**Revisit hook:** `limit: int = Query(200, ge=1, le=2000)` in `backend/app/api/offers.py`, the
matching `q.set('limit', '2000')` in `mobile/src/api.ts`, and `SERVE_LIMIT` in
`.github/scripts/verify_deals.py` — all three must move together, and the gate's truncation check
is what will tell you when.

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

---

## What happens when you press the Basket button a second time

**2026-08-19.** The deal detail's Basket button was add-only: `disabled` once the product was in
the basket, reading `In basket ✓`, with removal only on the Basket page. The user: *"pressing the
basket button should undo it."* Three forks came out of that.

### Fork 1 — how far does the undo reach?

| Option | Tradeoff |
|---|---|
| **A. The button toggles, and the left-swipe toggles with it** | One rule everywhere; the gesture and its button counterpart can't disagree. But a swipe is easy to trigger by accident, and it now removes rather than no-ops. |
| B. Only the button toggles; the swipe stays add-only | An accidental swipe stays harmless. But the two controls that are meant to be counterparts then behave differently, which is the kind of split that rots. |

**Chose A — the user's call.** The accidental-swipe worry is answered by making the affordance
honest rather than by making the gesture inert: the panel now reads **Remove** on an
already-basketed row, and the card already carries the cart marker, so the destructive version of
the gesture announces itself before you commit to it.

- B — **rejected**: two counterpart controls with different semantics.

### Fork 2 — does an undo prune the History entry the add created?

| Option | Tradeoff |
|---|---|
| **A. No — History stays append-only** | Consistent with the existing rule (only the History page's ✕ prunes) and with a test that already pinned it. Cost: a mis-tap leaves one row in History. |
| B. Yes — the undo fully reverses | Matches the intuition that undo means undo. But it needs bookkeeping to tell "the entry I just created" from one added last week, and it contradicts the append-only contract. |

**Chose A — the user's call.** History answers "what have I shopped for", not "what is in my
basket right now"; the basket already answers the second.

- B — **deferred — worth trying** if mis-taps turn out to litter History in practice.
  **Revisit hook:** `recordInHistory` in `DealsScreen.tsx` would have to return whether it
  inserted, and the toggle would remember that for the session.

### Fork 3 — the coarse key

Not a fork so much as a consequence worth recording. `resolveBasketItem` collapses two melons —
or two pastas — onto one basket row. Under a toggle, swiping product B removes the row product A
added. That was accepted rather than fixed (a finer key would split "I want yoghurt" into a row
per brand, which is not how the basket is meant to work), on the condition that **every affordance
is driven by the resolved key**: the card marker, the button label, and the swipe panel's word all
flip together. Verified live — adding a KNORR Carbonara marked the Delverde Teigwaren too, and
exactly those two rows' panels changed to Remove.

**Revisit hook:** `basketResolve.ts` `resolveBasketItem`. If the shared-row behaviour ever reads
as a bug rather than as the sub-category model working, that is the function to change — and the
three affordances above are what would need to follow it.
