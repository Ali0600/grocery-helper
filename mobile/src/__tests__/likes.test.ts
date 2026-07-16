import { isLiked, likeKey, matchLiked, onSaleCount, resolveLike } from '../likes';
import { LikedItem } from '../types';
import { makeOffer } from './fixtures';

const like = (over: Partial<LikedItem> = {}): LikedItem => ({
  key: 'mccain golden longs',
  name: 'McCain Golden Longs',
  brand: 'McCain',
  group: null,
  groupLabel: null,
  chain: 'lidl',
  likedPriceCents: 299,
  likedAt: 1,
  ...over,
});

describe('resolveLike', () => {
  it('snapshots the product identity with a normalized key', () => {
    const item = resolveLike(
      makeOffer({ name: 'McCain Golden Longs', brand: 'McCain', chain: 'edeka', price_cents: 299 }),
    );
    expect(item.key).toBe('mccain golden longs');
    expect(item.name).toBe('McCain Golden Longs');
    expect(item.brand).toBe('McCain');
    expect(item.chain).toBe('edeka');
    expect(item.likedPriceCents).toBe(299);
  });
});

describe('matchLiked — exact tier', () => {
  it('matches the same name case/punctuation-insensitively, across chains, cheapest first', () => {
    const offers = [
      makeOffer({ name: 'MCCAIN Golden-Longs', chain: 'edeka', price_cents: 349 }),
      makeOffer({ name: 'McCain Golden Longs', chain: 'lidl', price_cents: 299 }),
      makeOffer({ name: 'McCain Frites', chain: 'lidl', price_cents: 199 }),
    ];
    const m = matchLiked(like(), offers);
    expect(m.exact.map((o) => o.price_cents)).toEqual([299, 349]);
    expect(m.related).toEqual([]); // an exact hit suppresses the fallback
    expect(m.relatedLabel).toBeNull();
  });

  it('keeps umlauts significant (Käse is not Kase)', () => {
    const offers = [makeOffer({ name: 'Gouda Kase' })];
    const m = matchLiked(like({ key: 'gouda käse', name: 'Gouda Käse' }), offers);
    expect(m.exact).toEqual([]);
  });
});

describe('matchLiked — brand fallback (the renamed-product case)', () => {
  it('falls back to the brand when the exact name is gone, with the rename ranked first', () => {
    // The user's literal scenario: next week the flyer prints "McCain Golden Long".
    const offers = [
      makeOffer({ name: 'McCain Frites Originales', brand: 'McCain', price_cents: 149 }),
      makeOffer({ name: 'McCain Golden Long', brand: 'McCain', price_cents: 279 }),
      makeOffer({ name: 'Wagner Pizza', brand: 'Wagner', price_cents: 199 }),
    ];
    const m = matchLiked(like(), offers);
    expect(m.exact).toEqual([]);
    // "Golden Long" shares 2 name words with the liked product; Frites shares 1 (mccain).
    expect(m.related.map((o) => o.name)).toEqual([
      'McCain Golden Long',
      'McCain Frites Originales',
    ]);
    expect(m.relatedLabel).toBe('More from McCain');
  });

  it('matches brand across the feed casing drift (ALESTO vs Alesto)', () => {
    const offers = [makeOffer({ name: 'ALESTO Cashewkerne', brand: 'ALESTO' })];
    const m = matchLiked(like({ key: 'alesto nussmix', name: 'Alesto Nussmix', brand: 'Alesto' }), offers);
    expect(m.related).toHaveLength(1);
  });

  it('finds the brand inside the name when offer.brand is null (token containment)', () => {
    const offers = [makeOffer({ name: 'McCain Ofen Frites', brand: null })];
    const m = matchLiked(like(), offers);
    expect(m.related).toHaveLength(1);
  });

  it('does not fire a short brand mid-word (tokens, not substrings)', () => {
    // brand "ja!" normalizes to "ja" — it must not match a name merely CONTAINING "ja".
    const offers = [makeOffer({ name: 'Jagdwurst geräuchert', brand: null })];
    const m = matchLiked(like({ key: 'ja h milch', name: 'ja! H-Milch', brand: 'ja!' }), offers);
    expect(m.related).toEqual([]);
  });

  it('never leaks another brand into the fallback', () => {
    const offers = [
      makeOffer({ name: 'Wagner Golden Longs', brand: 'Wagner' }), // shares name words, wrong brand
    ];
    const m = matchLiked(like(), offers);
    expect(m.related).toEqual([]);
    expect(m.relatedLabel).toBeNull(); // no matches → no dangling section title
  });

  it('does not drag in wrong-brand items for house brands that are also descriptors', () => {
    // Real brands in the feed: Lidl sells "Deluxe" and "BBQ" as brands, and those words
    // also appear in unrelated products' NAMES. Matching the name would fill
    // "More from Deluxe" with a beer.
    const offers = [
      makeOffer({ name: 'Trabi Deluxe Pils', brand: 'Trabi', price_cents: 69 }),
      makeOffer({ name: 'KoRo Protein Bar Deluxe', brand: 'KoRo', price_cents: 199 }),
      makeOffer({ name: 'Deluxe Bruschetta', brand: 'Deluxe', price_cents: 249 }), // the real one
    ];
    const m = matchLiked(like({ key: 'deluxe pesto', name: 'Deluxe Pesto', brand: 'Deluxe' }), offers);
    expect(m.related.map((o) => o.name)).toEqual(['Deluxe Bruschetta']);
  });

  it('still matches a brand nested inside a longer brand string', () => {
    // The distributor case the name-fallback existed for: don't over-tighten it away.
    const offers = [makeOffer({ name: 'Cookie Dough', brand: "Langnese Ben & Jerry's" })];
    const m = matchLiked(
      like({ key: 'ben jerry s peace', name: "Ben & Jerry's Peace", brand: "Ben & Jerry's" }),
      offers,
    );
    expect(m.related).toHaveLength(1);
  });

  it('caps the fallback list', () => {
    const offers = Array.from({ length: 12 }, (_, i) =>
      makeOffer({ name: `McCain Produkt ${i}`, brand: 'McCain', price_cents: 100 + i }),
    );
    const m = matchLiked(like(), offers);
    expect(m.related.length).toBeLessThanOrEqual(8);
  });
});

describe('matchLiked — group fallback (brandless products)', () => {
  const tomatoLike = like({
    key: 'rispentomaten',
    name: 'Rispentomaten',
    brand: null,
    group: 'tomate',
    groupLabel: 'Tomaten',
  });

  it('falls back to the product sub-group when there is no brand', () => {
    const offers = [
      makeOffer({ name: 'Bio Cherrytomaten', group: 'tomate', price_cents: 249 }),
      makeOffer({ name: 'Salatgurke', group: 'gurke', price_cents: 79 }),
    ];
    const m = matchLiked(tomatoLike, offers);
    expect(m.related.map((o) => o.name)).toEqual(['Bio Cherrytomaten']);
    expect(m.relatedLabel).toBe('Other Tomaten');
  });

  it('returns nothing for a brandless, groupless like whose name is gone', () => {
    const m = matchLiked(like({ key: 'x', name: 'X', brand: null, group: null }), [
      makeOffer({ name: 'Y' }),
    ]);
    expect(m.exact).toEqual([]);
    expect(m.related).toEqual([]);
    expect(m.relatedLabel).toBeNull();
  });
});

describe('onSaleCount', () => {
  it('counts only likes with an exact match on sale now', () => {
    const offers = [
      makeOffer({ name: 'McCain Golden Longs' }),
      makeOffer({ name: 'McCain Frites', brand: 'McCain' }), // brand-only ≠ on sale again
    ];
    const likes = [
      like(), // exact match → counts
      like({ key: 'alesto nussmix', name: 'Alesto Nussmix', brand: 'Alesto' }), // only brand-level → no
    ];
    expect(onSaleCount(likes, offers)).toBe(1);
    expect(onSaleCount([], offers)).toBe(0);
    expect(onSaleCount(likes, [])).toBe(0);
  });
});

describe('likeKey / isLiked', () => {
  it('likeKey is the identity resolveLike persists — one definition, not two', () => {
    const o = makeOffer({ name: 'McCain Golden Longs' });
    expect(likeKey(o)).toBe(resolveLike(o).key);
    expect(likeKey(o)).toBe('mccain golden longs'); // normName-based
  });

  it('isLiked matches on product identity, not offer.id (ids churn weekly)', () => {
    const liked = resolveLike(makeOffer({ name: 'McCain Golden Longs' }));
    // Next week: same product, brand-new id and price.
    const nextWeek = makeOffer({ name: 'MCCAIN  Golden-Longs!', price_cents: 199 });
    expect(isLiked(nextWeek, [liked])).toBe(true);
    expect(isLiked(makeOffer({ name: 'Wagner Pizza' }), [liked])).toBe(false);
    expect(isLiked(nextWeek, [])).toBe(false);
  });
});
