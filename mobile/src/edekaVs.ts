// Pure core for the "EDEKA vs E center" page. E center (EDEKA's hypermarket format,
// chain "edeka_center") carries more items than a regular EDEKA, so this diffs the two
// flyers by product **name**: the same-named items whose price differs (cheapest per
// chain, biggest gap first) and the items only E center has. Name-matched because the
// user asked for "same name, different price"; the sub-group taxonomy (offer.group) is
// coarser. No React/RN imports → unit-testable. Uses only served fields (chain / name /
// price_cents), so it's display-only — no backend.
import { Offer } from './types';

// Exported so the deals list's duplicate filter (dealFilters.ts) keys off the SAME chain
// slugs and the same "same product" definition — the two must never drift apart.
export const EDEKA = 'edeka';
export const ECENTER = 'edeka_center';

/** Normalise a product name to a match key: lowercase, punctuation→spaces, collapsed. */
export function normName(name: string): string {
  return (name || '')
    .toLowerCase()
    .replace(/[^a-z0-9äöüß]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export type PriceDiffRow = {
  key: string; // normalised name
  label: string; // display name (the E center offer's)
  edeka: Offer; // cheapest EDEKA offer for this name
  ecenter: Offer; // cheapest E center offer for this name
  cheaper: 'edeka' | 'ecenter';
  gapCents: number; // absolute price difference (drives row order)
};

export type EdekaVsResult = {
  priceDiffs: PriceDiffRow[]; // shared name, price differs — biggest gap first
  ecenterOnly: Offer[]; // cheapest E center offer per name EDEKA doesn't have, A–Z
  hasBoth: boolean; // both chains present in the loaded set
};

// Keep the cheapest offer per normalised name for one chain. Exported: the deals list's
// E-center duplicate filter needs the identical lookup (see dealFilters.ts).
export function cheapestByName(offers: Offer[]): Map<string, Offer> {
  const m = new Map<string, Offer>();
  for (const o of offers) {
    const k = normName(o.name);
    if (!k) continue;
    const cur = m.get(k);
    if (!cur || o.price_cents < cur.price_cents) m.set(k, o);
  }
  return m;
}

/**
 * Diff EDEKA vs E center by product name. `priceDiffs` are names both stores list at a
 * different (cheapest) price; `ecenterOnly` are names only E center lists. Other chains
 * (lidl/rewe) are ignored. Same-name-same-price items appear in neither list.
 */
export function buildEdekaVs(offers: Offer[]): EdekaVsResult {
  const edekaOffers = offers.filter((o) => o.chain === EDEKA);
  const ecenterOffers = offers.filter((o) => o.chain === ECENTER);
  const ed = cheapestByName(edekaOffers);
  const ec = cheapestByName(ecenterOffers);

  const priceDiffs: PriceDiffRow[] = [];
  const ecenterOnly: Offer[] = [];
  for (const [k, ecOffer] of ec) {
    const edOffer = ed.get(k);
    if (!edOffer) {
      ecenterOnly.push(ecOffer);
    } else if (edOffer.price_cents !== ecOffer.price_cents) {
      priceDiffs.push({
        key: k,
        label: ecOffer.name,
        edeka: edOffer,
        ecenter: ecOffer,
        cheaper: ecOffer.price_cents < edOffer.price_cents ? 'ecenter' : 'edeka',
        gapCents: Math.abs(edOffer.price_cents - ecOffer.price_cents),
      });
    }
  }

  priceDiffs.sort((a, b) => b.gapCents - a.gapCents || a.label.localeCompare(b.label));
  ecenterOnly.sort((a, b) => a.name.localeCompare(b.name));

  return { priceDiffs, ecenterOnly, hasBoth: edekaOffers.length > 0 && ecenterOffers.length > 0 };
}
