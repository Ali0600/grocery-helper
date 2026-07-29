// Pure core for the "History" page: adding a deal to your basket records the product, and the
// page re-checks each recorded product against the currently loaded offers. Offer ids churn
// weekly, so an entry persists the product's IDENTITY (normalized name + brand + group) and
// matches are recomputed each session — the same contract as the Basket wishlist.
//
// History is APPEND-ONLY: taking something out of this week's basket doesn't erase that you
// shopped for it. The page's ✕ is the only way to prune.
//
// Matching tiers (deterministic, exclusive) — unchanged from the "Likes" page this replaces:
//   1. exact  — normName equality (the EdekaVs "same item" semantics: case/punctuation-
//               insensitive, umlauts significant, cross-chain).
//   2. related — the flyer renamed or rotated the product ("McCain Golden Longs" →
//               "McCain Golden Long"): fall back to the BRAND's products, ranked by how
//               many name words they share with the recorded product (so the rename lands
//               first), then price. Brandless items (18% of offers) fall back to the
//               product sub-group instead ("Rispentomaten" → other Tomaten offers).
// No React/RN imports → unit-testable.
import { normName } from './edekaVs';
import { HistoryItem, Offer } from './types';

/** How many fallback suggestions a History row shows before it stops being "quick". */
const RELATED_CAP = 8;

/** The stable identity of a recorded product. One definition, used both to persist an entry
 * and to ask "is this already recorded?" — don't call `resolveHistoryEntry` just to read a
 * key, it stamps `Date.now()`. */
export const historyKey = (offer: Offer): string => normName(offer.name);

/** Is this offer's product already in History? (Keys off the product identity, not `offer.id`
 * — ids churn weekly, so the answer stays right across flyer weeks.) */
export const inHistory = (offer: Offer, items: HistoryItem[]): boolean =>
  items.some((l) => l.key === historyKey(offer));

/** Snapshot an offer's product identity + the price you paid, as a persistable entry. */
export function resolveHistoryEntry(offer: Offer): HistoryItem {
  return {
    key: historyKey(offer),
    name: offer.name,
    brand: offer.brand,
    group: offer.group,
    groupLabel: offer.group_label,
    chain: offer.chain,
    addedPriceCents: offer.price_cents,
    addedAt: Date.now(),
  };
}

export type HistoryMatch = {
  exact: Offer[]; // same product on sale now, cheapest first ([] if none)
  related: Offer[]; // brand/group fallback when exact is empty, best-first, capped
  relatedLabel: string | null; // "More from McCain" / "Other Tomaten"
};

const tokens = (s: string): string[] => normName(s).split(' ').filter(Boolean);

/** Brand equality that survives the feed's casing drift (ALESTO vs Alesto — 61 brands
 * have variants in one week alone), then a name fallback for offers whose brand lives
 * only inside the name. Tokens, not substrings: a short brand like "ja!" must not fire
 * mid-word. */
function matchesBrand(offer: Offer, brand: string): boolean {
  const want = normName(brand);
  if (!want) return false;
  const offerBrand = normName(offer.brand ?? '');
  if (offerBrand === want) return true;
  const wantTokens = tokens(brand);
  if (!wantTokens.length) return false;
  if (offerBrand) {
    // The offer names a DIFFERENT brand — only a match if that brand *contains* the
    // recorded one ("Langnese Ben & Jerry's"). Searching its NAME here would wreck the
    // house brands that double as descriptors: recording Lidl's "Deluxe" would list
    // "Trabi Deluxe Pils" (a beer), and "BBQ" would list every Honey-BBQ chicken.
    const offerBrandTokens = new Set(tokens(offer.brand ?? ''));
    return wantTokens.every((t) => offerBrandTokens.has(t));
  }
  // Brandless offer (18% of the feed): the brand often appears only in the name.
  const nameTokens = new Set(tokens(offer.name));
  return wantTokens.every((t) => nameTokens.has(t));
}

/** Rank fallback offers: most shared name-words with the recorded product first (a renamed
 * "McCain Golden Long" outranks "McCain Frites"), then cheapest. */
function byNameOverlapThenPrice(recordedName: string) {
  const recorded = new Set(tokens(recordedName));
  const overlap = (o: Offer) => tokens(o.name).filter((t) => recorded.has(t)).length;
  return (a: Offer, b: Offer) => overlap(b) - overlap(a) || a.price_cents - b.price_cents;
}

/** Current on-sale status of one recorded product against the loaded offers. */
export function matchHistory(item: HistoryItem, offers: Offer[]): HistoryMatch {
  const exact = offers
    .filter((o) => normName(o.name) === item.key)
    .sort((a, b) => a.price_cents - b.price_cents);
  if (exact.length) return { exact, related: [], relatedLabel: null };

  let related: Offer[] = [];
  let relatedLabel: string | null = null;
  if (item.brand) {
    related = offers.filter((o) => matchesBrand(o, item.brand!));
    relatedLabel = `More from ${item.brand}`;
  } else if (item.group) {
    related = offers.filter((o) => o.group === item.group);
    relatedLabel = item.groupLabel ? `Other ${item.groupLabel}` : 'Similar products';
  }
  related = related.sort(byNameOverlapThenPrice(item.name)).slice(0, RELATED_CAP);
  return { exact: [], related, relatedLabel: related.length ? relatedLabel : null };
}

/** How many recorded products are on sale RIGHT NOW (exact matches only) — the header badge's
 * "worth opening History" signal. */
export function onSaleCount(items: HistoryItem[], offers: Offer[]): number {
  const names = new Set(offers.map((o) => normName(o.name)));
  return items.filter((l) => names.has(l.key)).length;
}
