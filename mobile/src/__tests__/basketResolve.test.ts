import { resolveBasketItem } from '../basketResolve';
import { makeOffer } from './fixtures';

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
