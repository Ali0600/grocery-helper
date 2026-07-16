import { SortMode } from './storage';

// The three sort modes + their labels, shared by the filter sheet (the selector)
// and the filter bar (the "Sort: …" summary). Order = display order.
export const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: 'price', label: 'Lowest price' },
  { value: 'discount', label: 'Biggest discount' },
  { value: 'unit', label: 'Cheapest €/kg' },
];

export const sortLabel = (mode: SortMode): string =>
  SORT_OPTIONS.find((o) => o.value === mode)?.label ?? '';

// Categories that keep the "Biggest discount" default. Inside a FOOD category €/kg is the
// better default on both counts: it's the axis you actually shop a category on, and it's far
// better covered — measured on a Berlin PLZ, €/kg beats discount in every category except
// household (72% vs 34% overall; fruits 77% vs 47%, pantry 93% vs 18%), because REWE/ALDI
// mostly publish no strike price so most offers have no discount_pct to rank by.
// household is the only non-food category (the classifier's non-food path lands there) and is
// the one place discount wins on coverage (36% vs 25%), so it stays. Everything else — incl.
// `other`/`vegan` and any future food category — gets €/kg. To retune, add a slug here.
const DISCOUNT_DEFAULT_CATEGORIES = new Set<string>(['household']);

/** The sort a category starts on before the user picks anything for it. "All" (no category)
 * keeps discount — browsing for deals is the app's headline, and €/kg is only meaningful
 * *within* a comparable set (a cheese's €/kg vs a shampoo's says nothing). */
export function defaultSortForCategory(category: string | null): SortMode {
  if (!category) return 'discount';
  return DISCOUNT_DEFAULT_CATEGORIES.has(category) ? 'discount' : 'unit';
}

/** The sort actually in effect: the user's explicit per-category choice wins, else the
 * category's default, else (in "All") the persisted global mode. Pure — unit-tested. */
export function resolveSortMode(
  category: string | null,
  globalSort: SortMode,
  perCategory: Record<string, SortMode>,
): SortMode {
  if (!category) return globalSort;
  return perCategory[category] ?? defaultSortForCategory(category);
}
