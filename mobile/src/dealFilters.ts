// Pure deals-screen pipeline: chain derivation, the filter stack, the sort comparator,
// and the category grouping. Extracted from DealsScreen so it's unit-testable and so the
// screen can memoize it (the inline version re-ran 8+ passes over ~1400 offers on every
// keystroke). No React imports — `SectionListData` is type-only (erased at runtime).

import type { SectionListData } from 'react-native';

import { filterByVisibleStores } from './stores';
import { SortMode } from './storage';
import { Offer } from './types';

// Preferred order for the store filter; any other chains follow, alphabetically.
export const CHAIN_ORDER = ['lidl', 'rewe', 'edeka', 'edeka_center'];

/** Chains present in the loaded set, CHAIN_ORDER first, unknown chains appended A–Z. */
export function presentChains(offers: Offer[]): string[] {
  const set = new Set(offers.map((o) => o.chain));
  const ordered = CHAIN_ORDER.filter((c) => set.has(c));
  const extra = [...set].filter((c) => !CHAIN_ORDER.includes(c)).sort();
  return [...ordered, ...extra];
}

/** Per-chain offer totals for the store-pill counts (static, whole-set). */
export function chainCounts(offers: Offer[]): Record<string, number> {
  return offers.reduce<Record<string, number>>((acc, o) => {
    acc[o.chain] = (acc[o.chain] ?? 0) + 1;
    return acc;
  }, {});
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
  return byNullsLast(a.discount_pct, b.discount_pct, 'desc'); // 'discount': biggest % off
}

export type DealFilterOptions = {
  showNonFood: boolean;
  hiddenStores: string[];
  specialDays: boolean;
  bioOnly: boolean;
  query: string;
  selected: string | null; // selected category chip (ignored while searching)
};

/**
 * The deals-list filter stack, in its long-standing order: non-food → hidden stores →
 * special-days → bio → search/category. The special-days and bio lenses only apply when
 * the loaded set actually contains such offers (same guard the screen always had), so a
 * stale toggle can't filter the list to empty.
 */
export function filterDeals(offers: Offer[], opts: DealFilterOptions): Offer[] {
  const foodBase = opts.showNonFood ? offers : offers.filter((o) => o.category !== 'household');
  const storeBase = filterByVisibleStores(foodBase, opts.hiddenStores);
  const hasDayLimited = offers.some((o) => o.day_limited);
  const base =
    opts.specialDays && hasDayLimited ? storeBase.filter((o) => o.day_limited) : storeBase;
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

// Per-section metadata for the grouped (category) view. `label === null` renders no
// header; `muted` is the small "More" header above the trailing single-offer bucket.
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

// Turn the already-filtered + sorted category view into sections: each product with
// 2+ offers becomes a headed comparison group (biggest first, then A–Z); single-offer
// and ungrouped items collect into one trailing bucket sorted by the active toggle.
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
    if (items.length >= 2) {
      groups.push({
        key,
        data: withinGroup(items, mode),
        label: items[0].group_label ?? key,
        count: items.length,
        fromCents: Math.min(...items.map((o) => o.price_cents)),
        muted: false,
      });
    } else {
      tail.push(items[0]); // a lone product has nothing to compare — send it down
    }
  });
  groups.sort((x, y) => y.count - x.count || (x.label ?? '').localeCompare(y.label ?? ''));

  const tailSorted = [...tail].sort((a, b) => compareOffers(a, b, mode));
  if (tailSorted.length) {
    groups.push({
      key: '__rest__',
      data: tailSorted,
      label: groups.length ? 'More' : null, // only label the bucket when groups sit above
      count: tailSorted.length,
      fromCents: null,
      muted: true,
    });
  }
  return groups;
}
