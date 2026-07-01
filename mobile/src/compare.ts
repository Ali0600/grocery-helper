// Pure comparison core for the "Compare Stores" page (product price face-off).
// Groups the loaded offers by product sub-group (offer.group, e.g. "avocado") within a
// category, and lines up each selected store's cheapest price for that sub-group so they
// can be compared side by side. No React/RN imports → unit-testable.

import { Offer } from './types';

export type CompareCell = {
  chain: string;
  offer: Offer | null; // the store's cheapest offer for this sub-group, or null (no match)
  isCheapest: boolean; // the (first) lowest-priced cell in the row
};

export type CompareRow = {
  key: string; // sub-group key (offer.group)
  label: string; // sub-group label (offer.group_label)
  cells: CompareCell[]; // one per selected chain, in the given chain order
  spreadCents: number; // max − min among the stores that have it (drives row order)
};

/**
 * Build the face-off rows for a category across the selected stores. A row is a product
 * sub-group present at **≥2** of the selected chains (nothing to compare otherwise),
 * with each chain's cheapest offer; rows are sorted by biggest price spread first.
 * Offers without a sub-group (`group == null`, e.g. many packaged goods) are excluded.
 */
export function buildComparison(
  offers: Offer[],
  chains: string[],
  category: string | null,
): CompareRow[] {
  const chainSet = new Set(chains);
  const groups = new Map<string, { label: string; perChain: Map<string, Offer> }>();

  for (const o of offers) {
    if (!o.group) continue;
    if (!chainSet.has(o.chain)) continue;
    if (category && o.category !== category) continue;
    const g = groups.get(o.group) ?? { label: o.group_label ?? o.group, perChain: new Map() };
    const cur = g.perChain.get(o.chain);
    if (!cur || o.price_cents < cur.price_cents) g.perChain.set(o.chain, o); // keep cheapest
    groups.set(o.group, g);
  }

  const rows: CompareRow[] = [];
  for (const [key, g] of groups) {
    const present = [...g.perChain.values()];
    if (present.length < 2) continue; // need ≥2 stores for a real face-off
    const min = Math.min(...present.map((o) => o.price_cents));
    const max = Math.max(...present.map((o) => o.price_cents));
    let cheapestMarked = false;
    const cells: CompareCell[] = chains.map((chain) => {
      const offer = g.perChain.get(chain) ?? null;
      const isCheapest = !!offer && offer.price_cents === min && !cheapestMarked;
      if (isCheapest) cheapestMarked = true; // on a tie, flag only the first (in chain order)
      return { chain, offer, isCheapest };
    });
    rows.push({ key, label: g.label, cells, spreadCents: max - min });
  }

  rows.sort((a, b) => b.spreadCents - a.spreadCents || a.label.localeCompare(b.label));
  return rows;
}
