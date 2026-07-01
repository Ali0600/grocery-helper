// Resolve a swiped offer to the SAME basket item the "+" button would add: map the
// offer's product sub-group (the section header the user sees, e.g. "Melone") to a
// catalog item, so swipe-add == "+"-add. Falls back to synthesizing the sub-group when
// the catalog doesn't have it, and to a name-based item when the offer has no sub-group
// at all. Pure — reuses basket.ts + catalog.ts, no React/RN imports (unit-testable).

import { norm, offerMatchesItem } from './basket';
import { CatalogItem, GROCERY_CATALOG } from './catalog';
import { BasketItem, Offer } from './types';

// The exact shape the "+" button pushes (see BasketModal `addCatalog`).
function toItem(c: CatalogItem): BasketItem {
  return { key: c.key, label: c.en, keywords: c.keywords, exclude: c.exclude };
}

// Most specific catalog item matching this offer by name: longest matched keyword wins,
// with a same-category tiebreak — mirrors product_group's specific-before-generic order
// (so "Hähnchenbrust" beats "Hähnchen").
function reverseMatch(offer: Offer): CatalogItem | null {
  const hay = norm(`${offer.name} ${offer.brand ?? ''}`);
  let best: CatalogItem | null = null;
  let bestScore = -1;
  for (const c of GROCERY_CATALOG) {
    if (!offerMatchesItem(offer, toItem(c))) continue;
    const longest = c.keywords.reduce((m, kw) => (hay.includes(norm(kw)) ? Math.max(m, kw.length) : m), 0);
    const score = longest + (c.category === offer.category ? 0.5 : 0);
    if (score > bestScore) {
      bestScore = score;
      best = c;
    }
  }
  return best;
}

export function resolveBasketItem(offer: Offer): BasketItem {
  // 1. The offer's sub-group IS the sub-category the user sees ("Melone"). Map it to a
  //    catalog item by its German label/keyword, so the added entry equals a "+" add.
  if (offer.group) {
    const label = offer.group_label ?? offer.group;
    const nl = norm(label);
    const hit =
      GROCERY_CATALOG.find((c) => norm(c.de) === nl) ??
      GROCERY_CATALOG.find((c) => c.keywords.some((kw) => norm(kw) === nl));
    if (hit) return toItem(hit);
    // No catalog entry for this sub-group → keep it as its own sub-category.
    return { key: `grp:${offer.group}`, label, keywords: [nl] };
  }
  // 2. No sub-group → reverse-match the catalog by name (the same signal the basket uses).
  const c = reverseMatch(offer);
  if (c) return toItem(c);
  // 3. Nothing matched → a specific item straight from the offer.
  return { key: `ofr:${norm(offer.name)}`, label: offer.name, keywords: [norm(offer.name)] };
}
