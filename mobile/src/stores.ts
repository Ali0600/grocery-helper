import { chainLabel } from './chains';
import { Offer } from './types';

// Multi-select store visibility for the deals list. We track the HIDDEN chains (a
// hidden-set), so the default (empty) shows everything and any new/unknown chain
// defaults to visible. `presentChains` = the chains actually loaded for the current PLZ.

// Toggle a chain's visibility. Guard: never hide the *last* visible present chain, so the
// deals list can't end up empty (returns the input unchanged if the toggle would do that).
export function toggleHiddenStore(
  hidden: string[],
  chain: string,
  presentChains: string[],
): string[] {
  if (hidden.includes(chain)) {
    return hidden.filter((c) => c !== chain); // un-hide: show it again
  }
  const stillVisible = presentChains.filter((c) => c !== chain && !hidden.includes(c));
  if (presentChains.includes(chain) && stillVisible.length === 0) {
    return hidden; // blocked — keep at least one present store visible
  }
  return [...hidden, chain];
}

// --- The "Only show" lens: which of your stores the deals list is showing right now ------
//
// A SECOND, narrower control than the hidden-set above, and the two must not be re-merged:
// `hiddenStores` is membership (which chains exist for you at all — it also scopes Basket,
// Recipes and Compare), while the lens is a deals-list view over the stores you already keep.
// Empty = All. It composes AFTER the hidden-set, so it can never lens a hidden store back in.

// Add/remove a chain. Uncapped — unlike the Recipes "Shop at" scope, which caps at two
// because a recipe is one shopping trip; this is a view. Deliberately has NO never-empty
// guard (the mirror of `toggleHiddenStore`'s): here empty MEANS all, so clearing the last
// pick is the way back — a guard would make the lens inescapable from the sheet.
export function toggleStoreLens(lens: string[], chain: string): string[] {
  return lens.includes(chain) ? lens.filter((c) => c !== chain) : [...lens, chain];
}

// The lens actually in effect: the selection narrowed to `available` (the chains the user can
// still see), in `available`'s order. Three rules:
//   * PARTIAL — ['rewe','edeka'] where only edeka is available lenses to edeka, not a no-op;
//   * EMPTY INTERSECTION -> [] — a stale pick (store removed, PLZ switched) must never empty
//     the list. This is what makes persisting the selection safe;
//   * FULL COVERAGE -> [] — selecting every available chain filters nothing out, so it IS
//     "All". Otherwise the bar would show a chip whose ✕ does nothing, and "All" would read
//     inactive while every chain pill is lit.
// Ordering by `available` (not tap order) keeps the result canonical, so the same selection
// can't produce two different chip labels or two different memo inputs.
export function activeStoreLens(lens: string[], available: string[]): string[] {
  if (!lens.length) return [];
  const active = available.filter((c) => lens.includes(c));
  return active.length === available.length ? [] : active;
}

// The bar chip's text. Two names stay scannable at 375pt; beyond that the names stop reading
// faster than a count, and since the chip row scrolls horizontally a long label pushes the
// sort button off-screen rather than truncating.
const LENS_NAMES_MAX = 2;
export function storeLensLabel(active: string[]): string {
  return active.length <= LENS_NAMES_MAX
    ? `Only ${active.map(chainLabel).join(' · ')}`
    : `Only ${active.length} stores`;
}

// Drop offers whose chain the user has hidden (identity fast-path when nothing is hidden).
export function filterByVisibleStores(offers: Offer[], hidden: string[]): Offer[] {
  return hidden.length ? offers.filter((o) => !hidden.includes(o.chain)) : offers;
}

// The present chains still shown, in present order — for the active-filter chip label.
export function visibleStoreChains(presentChains: string[], hidden: string[]): string[] {
  return presentChains.filter((c) => !hidden.includes(c));
}

// True when at least one *present* chain is hidden (so the store filter is visibly active).
// A hidden chain that isn't present for this PLZ doesn't count — nothing is filtered from view.
export function hasHiddenPresent(presentChains: string[], hidden: string[]): boolean {
  return presentChains.some((c) => hidden.includes(c));
}
