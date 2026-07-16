// Pure core for the "Likes" feature: right-swiping a deal likes the product; the Likes
// page re-checks each liked product against the currently loaded offers. Offer ids churn
// weekly, so a like persists the product's IDENTITY (normalized name + brand + group) and
// matches are recomputed each session — the same contract as the Basket wishlist.
//
// Matching tiers (deterministic, exclusive):
//   1. exact  — normName equality (the EdekaVs "same item" semantics: case/punctuation-
//               insensitive, umlauts significant, cross-chain).
//   2. related — the flyer renamed or rotated the product ("McCain Golden Longs" →
//               "McCain Golden Long"): fall back to the BRAND's products, ranked by how
//               many name words they share with the liked product (so the rename lands
//               first), then price. Brandless items (18% of offers) fall back to the
//               product sub-group instead ("Rispentomaten" → other Tomaten offers).
// No React/RN imports → unit-testable.
import { normName } from './edekaVs';
import { LikedItem, Offer } from './types';

/** How many fallback suggestions a Likes row shows before it stops being "quick". */
const RELATED_CAP = 8;

/** Snapshot an offer's product identity as a persistable like. */
export function resolveLike(offer: Offer): LikedItem {
  return {
    key: normName(offer.name),
    name: offer.name,
    brand: offer.brand,
    group: offer.group,
    groupLabel: offer.group_label,
    chain: offer.chain,
    likedPriceCents: offer.price_cents,
    likedAt: Date.now(),
  };
}

export type LikeMatch = {
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
    // liked one ("Langnese Ben & Jerry's"). Searching its NAME here would wreck the
    // house brands that double as descriptors: liking Lidl's "Deluxe" would list
    // "Trabi Deluxe Pils" (a beer), and "BBQ" would list every Honey-BBQ chicken.
    const offerBrandTokens = new Set(tokens(offer.brand ?? ''));
    return wantTokens.every((t) => offerBrandTokens.has(t));
  }
  // Brandless offer (18% of the feed): the brand often appears only in the name.
  const nameTokens = new Set(tokens(offer.name));
  return wantTokens.every((t) => nameTokens.has(t));
}

/** Rank fallback offers: most shared name-words with the liked product first (a renamed
 * "McCain Golden Long" outranks "McCain Frites"), then cheapest. */
function byNameOverlapThenPrice(likedName: string) {
  const liked = new Set(tokens(likedName));
  const overlap = (o: Offer) => tokens(o.name).filter((t) => liked.has(t)).length;
  return (a: Offer, b: Offer) => overlap(b) - overlap(a) || a.price_cents - b.price_cents;
}

/** Current on-sale status of one liked product against the loaded offers. */
export function matchLiked(item: LikedItem, offers: Offer[]): LikeMatch {
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

/** How many liked products are on sale RIGHT NOW (exact matches only) — the header
 * badge's "worth opening the Likes page" signal. */
export function onSaleCount(likes: LikedItem[], offers: Offer[]): number {
  const names = new Set(offers.map((o) => normName(o.name)));
  return likes.filter((l) => names.has(l.key)).length;
}
