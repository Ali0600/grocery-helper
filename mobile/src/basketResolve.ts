// Resolve a swiped offer to the SAME basket item the "+" button would add: map the
// offer's product sub-group (the section header the user sees, e.g. "Melone") to a
// catalog item, so swipe-add == "+"-add. Falls back to synthesizing the sub-group when
// the catalog doesn't have it, and to a name-based item when the offer has no sub-group
// at all. Pure — reuses basket.ts + catalog.ts, no React/RN imports (unit-testable).

import { norm, offerMatchesItem } from './basket';
import { CatalogItem, GROCERY_CATALOG } from './catalog';
import { BasketItem, Offer } from './types';

// The exact shape the "+" button pushes — exported so BasketModal uses THIS and not a
// fourth inline copy of the literal.
export function toItem(c: CatalogItem): BasketItem {
  return { key: c.key, label: c.en, keywords: c.keywords, exclude: c.exclude };
}

/**
 * The one rule that turns a product sub-group into a basket item — shared by the swipe
 * (`resolveBasketItem` below) and by BasketModal's "in this week's flyers" suggestions,
 * so both mint the SAME key and one product can never occupy two basket rows.
 *
 * `group` is the backend slug and is what the key is built from — never `norm(label)`.
 * The two disagree: `product_group._slug` hyphenates ("Ganze Bohnen" -> "ganze-bohnen")
 * while mobile `norm` keeps spaces ("ganze bohnen"). Keying off the label would give the
 * "+" path `grp:ganze bohnen` against the swipe's `grp:ganze-bohnen` — two rows, one
 * product, on a group that is live in coffee this week.
 *
 * A catalog hit wins over a synthesized item on purpose: catalog entries carry `exclude`
 * guards (apple excludes Apfelsaft, leek excludes Knoblauch) that a `grp:` item has not.
 */
export function subGroupItem(group: string, groupLabel?: string | null): BasketItem {
  const label = groupLabel ?? group;
  const nl = norm(label);
  const hit =
    GROCERY_CATALOG.find((c) => norm(c.de) === nl) ??
    GROCERY_CATALOG.find((c) => c.keywords.some((kw) => norm(kw) === nl));
  if (hit) return toItem(hit);
  // No catalog entry for this sub-group → keep it as its own sub-category.
  return { key: `grp:${group}`, label, keywords: [nl] };
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
  // 1. The offer's sub-group IS the sub-category the user sees ("Melone"), and it is the
  //    same rule BasketModal's flyer suggestions use — see `subGroupItem`.
  if (offer.group) return subGroupItem(offer.group, offer.group_label);
  // 2. No sub-group → reverse-match the catalog by name (the same signal the basket uses).
  const c = reverseMatch(offer);
  if (c) return toItem(c);
  // 3. Nothing matched → a specific item straight from the offer.
  return { key: `ofr:${norm(offer.name)}`, label: offer.name, keywords: [norm(offer.name)] };
}
