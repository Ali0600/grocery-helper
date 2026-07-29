// Pure deals-screen pipeline: chain derivation, the filter stack, the sort comparator,
// and the category grouping. Extracted from DealsScreen so it's unit-testable and so the
// screen can memoize it (the inline version re-ran 8+ passes over ~1400 offers on every
// keystroke). No React imports — `SectionListData` is type-only (erased at runtime).

import type { SectionListData } from 'react-native';

import { headlineDiscountPct } from './appPrice';
import { cheapestByName, ECENTER, EDEKA, normName } from './edekaVs';
import { filterHidden, onlyHidden } from './hidden';
import { filterByVisibleStores } from './stores';
import { SortMode } from './storage';
import { Offer } from './types';

// Preferred order for the store filter; any other chains follow, alphabetically.
export const CHAIN_ORDER = ['lidl', 'rewe', 'edeka', 'edeka_center', 'aldi'];

/** Chains present in the loaded set, CHAIN_ORDER first, unknown chains appended A–Z. */
export function presentChains(offers: Offer[]): string[] {
  const set = new Set(offers.map((o) => o.chain));
  const ordered = CHAIN_ORDER.filter((c) => set.has(c));
  const extra = [...set].filter((c) => !CHAIN_ORDER.includes(c)).sort();
  return [...ordered, ...extra];
}

/** Per-chain offer totals over whatever set you hand it. */
export function chainCounts(offers: Offer[]): Record<string, number> {
  return offers.reduce<Record<string, number>>((acc, o) => {
    acc[o.chain] = (acc[o.chain] ?? 0) + 1;
    return acc;
  }, {});
}

/** The counts shown on the Filters sheet's pills. */
export type FacetCounts = {
  chains: Record<string, number>;
  specialDays: number;
  bio: number;
  nonFood: number;
};

/**
 * "How many deals would I see if I turned this option on?" — for every pill in the sheet.
 *
 * Each facet is counted with **its own filter neutralised and every other one still applied**,
 * which is the only reading that makes the number actionable: counting with the facet ON would
 * show 0 for every store you haven't picked, and counting the whole set (what these pills used
 * to do) over-reports, because it ignores the E-center dedupe, hidden deals, search, and the
 * rest of the stack.
 *
 * The store counts are exactly additive with the list: the lens step is a plain per-chain
 * filter and everything after it is a per-offer predicate, so selecting {A,B} yields
 * `chains[A] + chains[B]` rows. (The one exception is the lens's own no-op guard — a chain
 * whose every offer is an E-center duplicate counts 0 and, if picked alone, no-ops to the full
 * list. Rare, and 0 is the honest thing to show.)
 *
 * Four passes over the loaded set, so callers should memoize and only ask while the sheet is
 * open — see DealsScreen.
 */
export function facetCounts(offers: Offer[], opts: DealFilterOptions): FacetCounts {
  const without = (over: Partial<DealFilterOptions>) => filterDeals(offers, { ...opts, ...over });
  return {
    chains: chainCounts(without({ storeLens: [] })),
    specialDays: without({ specialDays: false }).filter((o) => o.day_limited).length,
    bio: without({ bioOnly: false }).filter((o) => o.is_bio).length,
    // Non-food is the first step, so "how many would appear" means running with it shown.
    nonFood: without({ showNonFood: true }).filter((o) => o.category === 'household').length,
  };
}

/**
 * Drop E center offers that merely repeat EDEKA. E center is EDEKA's hypermarket format and a
 * separate chain, so the two flyers overlap heavily: measured on a Berlin PLZ, 103 of E center's
 * 272 products are also at EDEKA and **98% of those are priced identically** — pure noise in the
 * list. Only what E center actually adds should survive.
 *
 * An E center offer is dropped only when a same-named EDEKA offer exists AND the E center price is
 * **not lower** — a cheaper price isn't a duplicate, it's the better deal (Axe Duschgel: EDEKA 2,79
 * → E center 2,29). That exception is what makes this safe to apply silently: a dropped offer is
 * never cheaper than the EDEKA row that survives, so this can never remove a best price.
 *
 * No-ops when EDEKA isn't in the set (hidden via the store list, or absent for this PLZ) — the same
 * only-when-present guard the lens/special-days/bio steps use, so a product can never vanish from
 * both chains at once. Matching reuses edekaVs' `normName`/`cheapestByName`, so the list and the
 * "EDEKA vs E center" page always agree on what "the same product" means.
 */
export function dropEdekaCenterDuplicates(offers: Offer[]): Offer[] {
  const edekaByName = cheapestByName(offers.filter((o) => o.chain === EDEKA));
  if (edekaByName.size === 0) return offers; // no EDEKA to compare against → nothing to suppress
  return offers.filter((o) => {
    if (o.chain !== ECENTER) return true; // never touch EDEKA's own rows, or any other chain
    const twin = edekaByName.get(normName(o.name));
    if (!twin) return true; // only at E center — the deals worth showing
    return o.price_cents < twin.price_cents; // keep ONLY when E center genuinely undercuts EDEKA
  });
}

// Compare two values, sending nulls to the end regardless of direction.
function byNullsLast(a: number | null, b: number | null, dir: 'asc' | 'desc'): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  return dir === 'asc' ? a - b : b - a;
}

// The single source of truth for how offers are ordered, by the active sort mode. Used by
// the flat list, the within-group order, and the "More" bucket so they're always consistent.
export function compareOffers(a: Offer, b: Offer, mode: SortMode): number {
  if (mode === 'unit') return byNullsLast(a.unit_price_cents, b.unit_price_cents, 'asc');
  if (mode === 'price') return a.price_cents - b.price_cents; // cheapest absolute price
  // 'discount': biggest % off, with a Mit-App price counting as the deeper headline discount.
  return byNullsLast(headlineDiscountPct(a), headlineDiscountPct(b), 'desc');
}

export type DealFilterOptions = {
  showNonFood: boolean;
  /** Keys of deals the user dismissed from the deal detail (see hidden.ts). Active-only —
   * the caller passes `hiddenKeySet(...)`, which already drops expired hides. */
  hiddenKeys: Set<string>;
  /** Session-only lens: show ONLY hidden deals, so a hidden one can be reopened and un-hidden.
   * The Filters sheet is the only route back to a hidden deal's detail. */
  showHidden: boolean;
  hiddenStores: string[];
  /** The "Only show" lens — which of the user's stores the deals list is showing. EMPTY =
   * all of them. Multi-select and persisted, but still distinct from `hiddenStores`: that's
   * membership (it scopes Basket/Recipes/Compare too), this is a deals-list view over the
   * stores you already keep. It composes AFTER it, so it can't lens a hidden store into view. */
  storeLens: string[];
  specialDays: boolean;
  bioOnly: boolean;
  query: string;
  selected: string | null; // selected category chip (ignored while searching)
};

/**
 * The deals-list filter stack, in its long-standing order: non-food → hidden deals → hidden
 * stores → E-center duplicates → store lens → special-days → bio → search/category. The
 * store, special-days and bio lenses only apply when the loaded set actually contains such
 * offers (same guard the screen always had), so a stale toggle can't filter the list to empty.
 */
export function filterDeals(offers: Offer[], opts: DealFilterOptions): Offer[] {
  const foodBase = opts.showNonFood ? offers : offers.filter((o) => o.category !== 'household');
  // Hiding is the user's strongest "never show me this", so it runs first — and BEFORE the
  // E-center dedupe below, deliberately: hiding EDEKA's copy of a shared product should let E
  // center's twin surface, which falls out of this order for free. The lens inverts it, and is
  // the only way back to a hidden deal's detail (and so to its Un-Hide button).
  const hiddenBase = opts.showHidden
    ? onlyHidden(foodBase, opts.hiddenKeys)
    : filterHidden(foodBase, opts.hiddenKeys);
  const storeBase = filterByVisibleStores(hiddenBase, opts.hiddenStores);
  // Position is load-bearing, on both sides:
  //  * AFTER the store filter — if EDEKA is hidden, suppression must switch off, or the shared
  //    products would disappear from the list entirely instead of just showing E center's copy;
  //  * BEFORE the lens — lensing to "Only E center" strips EDEKA from the set, which would
  //    disable the guard and bring every duplicate back in the one view that most needs them gone.
  const dedupedBase = dropEdekaCenterDuplicates(storeBase);
  // Same only-when-present guard as special-days/bio below, but PARTIAL: keep the selected
  // chains that still have offers here, so a selection whose other chains were hidden
  // mid-session (or aren't in this PLZ) narrows to what survives instead of no-op'ing
  // wholesale. An empty intersection stays a full no-op — a stale lens must never empty the
  // list, which is what makes the selection safe to persist.
  // Tested against `dedupedBase`, NOT the raw `offers` arg that special-days/bio use: a chain
  // whose every offer is an E-center duplicate is "present" in `offers` but has nothing left
  // to show, so harmonising those guards would filter the list to empty.
  const lens = opts.storeLens.length
    ? opts.storeLens.filter((c) => dedupedBase.some((o) => o.chain === c))
    : opts.storeLens;
  const lensBase = lens.length ? dedupedBase.filter((o) => lens.includes(o.chain)) : dedupedBase;
  const hasDayLimited = offers.some((o) => o.day_limited);
  const base =
    opts.specialDays && hasDayLimited ? lensBase.filter((o) => o.day_limited) : lensBase;
  const hasBio = offers.some((o) => o.is_bio);
  const bioBase = opts.bioOnly && hasBio ? base.filter((o) => o.is_bio) : base;

  const q = opts.query.trim().toLowerCase();
  if (q) {
    return bioBase.filter(
      (o) => o.name.toLowerCase().includes(q) || (o.brand ?? '').toLowerCase().includes(q),
    );
  }
  return opts.selected ? bioBase.filter((o) => o.category === opts.selected) : bioBase;
}

// One category "shelf" on the personalized "My Categories" home: a header + a short preview of
// that category's best deals, with `total` so the header can say "See all 42". `data` is the
// preview slice; `total` is the full count (data.length may be < total when truncated).
export type MineSection = {
  slug: string;
  label: string;
  total: number;
  data: Offer[];
};

/**
 * Build the "My Categories" home from an already-filtered base. `base` MUST be the `filterDeals`
 * output with `selected: null` and `query: ''` — so the home inherits every list filter (hidden
 * deals, hidden stores, the E-center dedupe, the store lens, special-days, bio, non-food) and can
 * never drift from what the list would show.
 *
 * One shelf per slug in `myCategories`, IN THAT ORDER (the user's priority). Each shelf is the
 * category's offers sorted by that category's own sort (`sortFor(slug)` — €/kg for food) and sliced
 * to `previewCount`. A category with no offers this week is SKIPPED (no empty header). `total`
 * reflects the full count so the header's "See all N" is honest.
 */
export function buildMineSections(
  base: Offer[],
  myCategories: string[],
  labels: Record<string, string>,
  sortFor: (slug: string) => SortMode,
  previewCount = 5,
): MineSection[] {
  const byCat = new Map<string, Offer[]>();
  for (const o of base) {
    const arr = byCat.get(o.category);
    if (arr) arr.push(o);
    else byCat.set(o.category, [o]);
  }
  const sections: MineSection[] = [];
  for (const slug of myCategories) {
    const items = byCat.get(slug);
    if (!items || items.length === 0) continue; // skip a category with no deals this week
    const sorted = [...items].sort((a, b) => compareOffers(a, b, sortFor(slug)));
    sections.push({
      slug,
      // Prefer the served label; fall back to the offer's own label, then the slug — a shelf must
      // never render a blank title just because /api/categories hasn't loaded yet.
      label: labels[slug] ?? sorted[0].category_label ?? slug,
      total: sorted.length,
      data: sorted.slice(0, previewCount),
    });
  }
  return sections;
}

// One category card in the "My Categories" browser: the category, its full deal count, and a short
// list of its headline deals (the most-discounted first).
export type CategoryCard = {
  slug: string;
  label: string;
  total: number;
  top: Offer[];
};

/**
 * Build the category-browser cards from an already-filtered base (same contract as
 * `buildMineSections`: the `filterDeals` output with `selected: null` and `query: ''`, so the cards
 * inherit every list filter and can't drift from what the list would show).
 *
 * One card per slug in `order` that has offers; categories with none are skipped (no empty cards).
 * `top` is the category's **most-discounted** offers — and when fewer than `topCount` carry a
 * discount at all, the remainder is FILLED with the category's best remaining offers by its own
 * default sort (€/kg for food). Measured on a live set: 2 of 23 categories can't fill three from
 * discounts alone (Butter has 1, Eggs 0), and a half-empty card reads as broken — so the fill is the
 * difference between an honest card and a gap. Filled rows simply have no discount to badge.
 */
export function buildCategoryCards(
  base: Offer[],
  order: string[],
  labels: Record<string, string>,
  sortFor: (slug: string) => SortMode,
  topCount = 3,
): CategoryCard[] {
  const byCat = new Map<string, Offer[]>();
  for (const o of base) {
    const arr = byCat.get(o.category);
    if (arr) arr.push(o);
    else byCat.set(o.category, [o]);
  }
  const cards: CategoryCard[] = [];
  for (const slug of order) {
    const items = byCat.get(slug);
    if (!items || items.length === 0) continue;
    // Discounted first (compareOffers already sinks null discounts), then top up from the
    // category's own best-by-default-sort so the card always shows `topCount` rows when it can.
    const discounted = items
      .filter((o) => headlineDiscountPct(o) != null)
      .sort((a, b) => compareOffers(a, b, 'discount'))
      .slice(0, topCount);
    const chosen = new Set(discounted.map((o) => o.id));
    const filler = items
      .filter((o) => !chosen.has(o.id))
      .sort((a, b) => compareOffers(a, b, sortFor(slug)))
      .slice(0, Math.max(0, topCount - discounted.length));
    cards.push({
      slug,
      label: labels[slug] ?? items[0].category_label ?? slug,
      total: items.length,
      top: [...discounted, ...filler],
    });
  }
  return cards;
}

// Per-section metadata for the grouped (category) view. `label === null` renders no
// header; `muted` is the small "More" header above the trailing bucket of offers that
// carry no sub-group at all.
export type SectionMeta = {
  label: string | null;
  count: number;
  fromCents: number | null;
  muted: boolean;
};
export type DealSection = SectionListData<Offer, SectionMeta>;

// Within a comparison group, order by the active sort metric (cheapest €/kg, biggest
// discount, or lowest price) — same comparator as the flat list, so they stay consistent.
function withinGroup(items: Offer[], mode: SortMode): Offer[] {
  return [...items].sort((a, b) => compareOffers(a, b, mode));
}

// Turn the already-filtered + sorted category view into sections: EVERY product with a
// sub-group gets its own header (biggest first, then A–Z), even at one offer — the
// sub-category is the unit the user shops in and the unit the Basket keys on, so hiding
// it below one offer made a lone Kiwi unnameable. Only offers with no sub-group at all
// collect into the trailing bucket, sorted by the active toggle.
export function buildSections(sorted: Offer[], mode: SortMode): DealSection[] {
  const byGroup = new Map<string, Offer[]>();
  const tail: Offer[] = [];
  for (const o of sorted) {
    if (o.group) {
      const arr = byGroup.get(o.group);
      if (arr) arr.push(o);
      else byGroup.set(o.group, [o]);
    } else {
      tail.push(o);
    }
  }

  const groups: DealSection[] = [];
  byGroup.forEach((items, key) => {
    // Unconditional: a byGroup entry is created as [o] and only ever grown, so it can
    // never be empty — a length guard here would be a branch no test could ever fail.
    groups.push({
      key,
      data: withinGroup(items, mode),
      label: items[0].group_label ?? key,
      count: items.length,
      fromCents: Math.min(...items.map((o) => o.price_cents)),
      muted: false,
    });
  });
  groups.sort((x, y) => y.count - x.count || (x.label ?? '').localeCompare(y.label ?? ''));

  const tailSorted = [...tail].sort((a, b) => compareOffers(a, b, mode));
  if (tailSorted.length) {
    groups.push({
      key: '__rest__',
      data: tailSorted,
      // Only label the bucket when headed groups sit above it. Since every sub-group now
      // gets a header, the unlabelled case means "not one offer here carries a sub-group"
      // — i.e. a category `product_group` doesn't map (pantry, sweets, alcoholic, …),
      // which must keep rendering as a plain flat list.
      label: groups.length ? 'More' : null,
      count: tailSorted.length,
      fromCents: null,
      muted: true,
    });
  }
  return groups;
}
