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
