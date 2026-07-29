import { resolveBasketItem, subGroupItem } from '../basketResolve';
import { makeOffer } from './fixtures';

// `subGroupItem` is the ONE rule turning a sub-group into a basket item. The swipe
// (resolveBasketItem) and BasketModal's "in this week's flyers" chips both go through it,
// so they cannot drift into minting two keys for one product.
describe('subGroupItem — the shared sub-group → basket item rule', () => {
  it('is exactly what resolveBasketItem uses for an offer with a sub-group', () => {
    for (const [group, label] of [
      ['melone', 'Melone'], // has a catalog counterpart
      ['camembert', 'Camembert'], // does not
    ] as const) {
      const viaOffer = resolveBasketItem(makeOffer({ group, group_label: label }));
      expect(viaOffer).toEqual(subGroupItem(group, label));
    }
  });

  it('keys on the backend slug, NOT the normalized label', () => {
    // product_group._slug hyphenates ("Ganze Bohnen" → "ganze-bohnen") while mobile `norm`
    // keeps spaces. Keying off the label would give the chip `grp:ganze bohnen` against the
    // swipe's `grp:ganze-bohnen` — two basket rows for one product, on a group that is live
    // in coffee this week.
    expect(subGroupItem('ganze-bohnen', 'Ganze Bohnen').key).toBe('grp:ganze-bohnen');
  });

  it('falls back to the slug when the label is missing', () => {
    expect(subGroupItem('kohlrabi')).toEqual({
      key: 'grp:kohlrabi',
      label: 'kohlrabi',
      keywords: ['kohlrabi'],
    });
  });

  it('prefers a catalog item, so the substring guards come with it', () => {
    // A synthesized grp: item carries no `exclude`. Preferring the catalog is what keeps
    // "Lauch" from matching Knoblauch once these become one-tap chips rather than a
    // deliberate swipe on one specific offer.
    const leek = subGroupItem('lauch', 'Lauch');
    expect(leek.key).toBe('leek');
    expect(leek.exclude).toContain('knoblauch');
  });
});

describe('resolveBasketItem — offer with a product sub-group', () => {
  it('maps "Melone" to the catalog melon item (== the "+" add)', () => {
    const item = resolveBasketItem(
      makeOffer({ name: 'Wassermelone kernarm', group: 'melone', group_label: 'Melone', category: 'fruits' }),
    );
    expect(item).toEqual({ key: 'melon', label: 'Melon', keywords: ['melone'], exclude: undefined });
  });

  it('maps "Hähnchenbrust" to chicken-breast', () => {
    const item = resolveBasketItem(
      makeOffer({ name: 'Hähnchenbrustfilet', group: 'hahnchenbrust', group_label: 'Hähnchenbrust', category: 'poultry' }),
    );
    expect(item.key).toBe('chicken-breast');
    expect(item.label).toBe('Chicken breast');
  });

  it('maps a sub-group whose catalog label differs but a keyword matches (Traube → grape)', () => {
    const item = resolveBasketItem(
      makeOffer({ name: 'Tafeltrauben hell', group: 'traube', group_label: 'Traube', category: 'fruits' }),
    );
    expect(item.key).toBe('grape');
  });

  it('synthesizes a sub-category when the catalog has no entry (Camembert)', () => {
    const item = resolveBasketItem(
      makeOffer({ name: 'Camembert 45%', group: 'camembert', group_label: 'Camembert', category: 'cheese' }),
    );
    expect(item).toEqual({ key: 'grp:camembert', label: 'Camembert', keywords: ['camembert'] });
  });
});

describe('resolveBasketItem — offer without a sub-group (reverse-match)', () => {
  it('matches the catalog by name', () => {
    const item = resolveBasketItem(makeOffer({ name: 'Frische Erdbeeren 500g', group: null, category: 'fruits' }));
    expect(item.key).toBe('strawberry');
  });

  it('prefers the most specific catalog item (chicken-breast over chicken)', () => {
    const item = resolveBasketItem(makeOffer({ name: 'Hähnchenbrust natur', group: null, category: 'poultry' }));
    expect(item.key).toBe('chicken-breast');
  });

  it('falls back to a name-based item when nothing matches', () => {
    const item = resolveBasketItem(makeOffer({ name: 'Räuchertofu Natur', group: null, category: 'other' }));
    expect(item.key).toBe('ofr:rauchertofu natur');
    expect(item.label).toBe('Räuchertofu Natur');
  });
});

describe('resolveBasketItem — key stability (de-dupe)', () => {
  it('two different melon offers resolve to the same key', () => {
    const a = resolveBasketItem(makeOffer({ name: 'Bio Wassermelone', group: 'melone', group_label: 'Melone', category: 'fruits' }));
    const b = resolveBasketItem(makeOffer({ name: 'Honigmelone Stück', group: 'melone', group_label: 'Melone', category: 'fruits' }));
    expect(a.key).toBe(b.key);
    expect(a.key).toBe('melon');
  });
});
