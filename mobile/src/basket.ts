// Pure, deterministic basket logic — no React/React-Native imports, so it's trivial
// to unit-test later. Matches the user's wishlist items against the in-memory offer
// set and builds the cross-store shopping plan. Offers are German-named; matching
// folds umlauts on both sides (mirrors `backend/app/product_group.py` `_UMLAUT`).

import { BasketItem, Offer } from './types';

const UMLAUT: Record<string, string> = {
  ä: 'a',
  ö: 'o',
  ü: 'u',
  ß: 'ss',
  é: 'e',
  è: 'e',
  ê: 'e',
};

/** Lowercase + fold umlauts so "Möhre"/"Moehre"/"MÖHRE" all compare equal. */
export function norm(s: string): string {
  return (s || '').toLowerCase().replace(/[äöüßéèê]/g, (c) => UMLAUT[c] ?? c);
}

function haystack(o: Offer): string {
  return norm(`${o.name} ${o.brand ?? ''}`);
}

/** Does this offer match a basket item? Any keyword as a substring, no excluded term. */
export function offerMatchesItem(o: Offer, item: BasketItem): boolean {
  const hay = haystack(o);
  if (item.exclude && item.exclude.some((x) => hay.includes(norm(x)))) return false;
  return item.keywords.some((kw) => hay.includes(norm(kw)));
}

/** All offers matching an item, cheapest absolute price first. */
export function matchOffers(offers: Offer[], item: BasketItem): Offer[] {
  return offers.filter((o) => offerMatchesItem(o, item)).sort((a, b) => a.price_cents - b.price_cents);
}

/** Cheapest matching offer, or null if the item has no deal this week. */
export function bestMatch(offers: Offer[], item: BasketItem): Offer | null {
  let best: Offer | null = null;
  for (const o of offers) {
    if (!offerMatchesItem(o, item)) continue;
    if (!best || o.price_cents < best.price_cents) best = o;
  }
  return best;
}

// One basket item resolved against the current offers.
export type PlanLine = {
  item: BasketItem;
  offer: Offer | null; // the user's pick, else the cheapest match, else null
  matchCount: number; // how many offers match (drives the "N deals" affordance)
};

// Items whose chosen offer is at the same chain — one leg of the shopping trip.
export type StoreGroup = {
  chain: string;
  lines: PlanLine[];
  subtotalCents: number;
};

export type Plan = {
  lines: PlanLine[]; // one per basket item, in basket order
  byStore: StoreGroup[]; // groups with ≥1 chosen offer, priciest leg first
  totalCents: number; // sum of all chosen offers (cherry-picked across stores)
  matchedCount: number; // items with a deal
  missing: BasketItem[]; // items with no deal this week
  bestSingleChain: string | null; // single store covering the most items, cheapest
  savingsCents: number | null; // best-single total − cherry-pick total, when the
  // single store covers *every* matched item and splitting is cheaper (else null)
};

/**
 * Resolve every basket item to its chosen offer (the user's `pick` by offer id, else
 * the cheapest match), group the picks by store, and compare against the best single
 * store. `picks` maps a BasketItem.key to a chosen Offer.id (session-only).
 */
export function buildPlan(basket: BasketItem[], offers: Offer[], picks: Record<string, number>): Plan {
  const lines: PlanLine[] = basket.map((item) => {
    const matches = matchOffers(offers, item);
    const pickId = picks[item.key];
    const picked = pickId != null ? matches.find((o) => o.id === pickId) : undefined;
    return { item, offer: picked ?? matches[0] ?? null, matchCount: matches.length };
  });

  const withOffer = lines.filter((l): l is PlanLine & { offer: Offer } => l.offer != null);
  const totalCents = withOffer.reduce((s, l) => s + l.offer.price_cents, 0);
  const missing = lines.filter((l) => l.offer == null).map((l) => l.item);

  const groupMap = new Map<string, PlanLine[]>();
  for (const l of withOffer) {
    const arr = groupMap.get(l.offer.chain);
    if (arr) arr.push(l);
    else groupMap.set(l.offer.chain, [l]);
  }
  const byStore: StoreGroup[] = [...groupMap.entries()]
    .map(([chain, ls]) => ({
      chain,
      lines: ls,
      subtotalCents: ls.reduce((s, l) => s + (l.offer ? l.offer.price_cents : 0), 0),
    }))
    .sort((a, b) => b.subtotalCents - a.subtotalCents);

  // Best single store: the chain covering the most basket items (tie → cheapest sum),
  // mirroring the backend optimizer's single-store rule, but per-product.
  let bestSingleChain: string | null = null;
  let bestSingleTotal: number | null = null;
  let bestSingleCovered = -1;
  for (const chain of new Set(offers.map((o) => o.chain))) {
    const chainOffers = offers.filter((o) => o.chain === chain);
    let sum = 0;
    let covered = 0;
    for (const item of basket) {
      const m = bestMatch(chainOffers, item);
      if (m) {
        sum += m.price_cents;
        covered += 1;
      }
    }
    if (covered === 0) continue;
    if (covered > bestSingleCovered || (covered === bestSingleCovered && sum < (bestSingleTotal ?? Infinity))) {
      bestSingleCovered = covered;
      bestSingleChain = chain;
      bestSingleTotal = sum;
    }
  }

  // Only a like-for-like saving: the single store must cover *every* matched item.
  const savingsCents =
    bestSingleTotal != null && bestSingleCovered === withOffer.length ? bestSingleTotal - totalCents : null;

  return {
    lines,
    byStore,
    totalCents,
    matchedCount: withOffer.length,
    missing,
    bestSingleChain,
    savingsCents,
  };
}
