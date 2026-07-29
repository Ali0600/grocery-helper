// `nameKey` is the join key into the grocery-price-history dataset. It must agree EXACTLY with
// the collector's own normalizer, or a lookup silently misses and the product shows no history.
//
// Three tiers of proof, in increasing order of how much they'd catch:
//   1. the collector's own test vectors, ported verbatim — the contract it holds itself to;
//   2. the divergence table, which asserts BOTH `nameKey` and `normName` on the same inputs, so
//      that "these two look similar, let's unify them" fails five assertions carrying the reason;
//   3. a corpus check over real upstream rows: `nameKey(label) === name_key` for every one.
import { normName } from '../edekaVs';
import { nameKey } from '../nameKey';
import index from './fixtures/priceIndexSample.json';

// --- 1. Ported from grocery-price-history/src/normalize.test.ts -----------------------

describe('nameKey — the collector’s own vectors', () => {
  it('drops curly vs straight apostrophes', () => {
    expect(nameKey("Butcher's Angus Patties")).toBe(nameKey('Butcher’s Angus Patties'));
    expect(nameKey("Butcher's Angus Patties")).toBe('butchers angus patties');
  });

  it('strips decorative German quotes and the produce grade token', () => {
    expect(nameKey('REWE Feine Welt Essreife Avocado »Hass«, Kl. I')).toBe(
      nameKey('REWE Feine Welt Essreife Avocado Hass'),
    );
  });

  it('keeps umlauts and ß as word characters (unlike ASCII \\w)', () => {
    expect(nameKey('Möhren süß')).toBe('möhren süß');
  });

  it('does not strip "kl"-like fragments inside words', () => {
    expect(nameKey('Dunkle Schokolade 3')).toBe('dunkle schokolade 3');
    expect(nameKey('Klasse Käse')).toBe('klasse käse');
  });

  it('strips grade variants: Kl. II, Klasse 1', () => {
    expect(nameKey('Tomaten Kl. II')).toBe('tomaten');
    expect(nameKey('Äpfel Klasse 1')).toBe('äpfel');
  });

  it('maps punctuation to spaces and collapses whitespace', () => {
    expect(nameKey('Joghurt,  Natur - 3,8%')).toBe('joghurt natur 3 8');
  });

  it('only strips a grade when the digit ENDS the token — not mid-number', () => {
    // Not in the collector's own suite: found by sabotage. Dropping the grade regex's trailing
    // lookahead passes every other case here, but eats the leading digit of a real quantity —
    // "Tomaten Kl. 1000g" becomes "tomaten 000g", a wrong key that still looks plausible.
    expect(nameKey('Tomaten Kl. 1000g')).toBe('tomaten kl 1000g');
    expect(nameKey('Eis Klasse 12')).toBe('eis klasse 12');
    expect(nameKey('Wein Kl. IIII')).toBe('wein kl iiii');
  });

  it('handles null/undefined/empty', () => {
    expect(nameKey(null)).toBe('');
    expect(nameKey(undefined)).toBe('');
    expect(nameKey('  ')).toBe('');
  });
});

// --- 2. The divergence table ----------------------------------------------------------

describe('nameKey vs normName — two normalizers, on purpose', () => {
  // Measured on a real snapshot: they disagree on ~4% of names (55 of 1,388). The two columns
  // are asserted TOGETHER so neither can be "simplified" into the other:
  //   * normName is the app's PERSISTED identity (HistoryItem.key, HiddenItem.key's second
  //     half). Changing it orphans every entry already on a user's device, silently.
  //   * nameKey is a join key for one external dataset. Changing it breaks the join, loudly.
  // Note they diverge in BOTH directions: normName maps ' to a space and deletes accents;
  // nameKey deletes ' and keeps accents.
  const cases: [string, string, string][] = [
    ["Lay's Bugles", 'lay s bugles', 'lays bugles'],
    ["Ben's Original Express-Reis", 'ben s original express reis', 'bens original express reis'],
    ['NESCAFÉ Gold', 'nescaf gold', 'nescafé gold'],
    ['Emmi Caffè Latte', 'emmi caff latte', 'emmi caffè latte'],
    ["Schäfer's Weizenbrötchen", 'schäfer s weizenbrötchen', 'schäfers weizenbrötchen'],
  ];

  it.each(cases)('%s', (raw, expectedNormName, expectedNameKey) => {
    expect(normName(raw)).toBe(expectedNormName);
    expect(nameKey(raw)).toBe(expectedNameKey);
  });

  it('agrees on the plain majority — the divergence is the exception, not the rule', () => {
    for (const s of ['Milbona Gouda', 'Rispentomaten 500 g', 'Coca Cola Zero']) {
      expect(nameKey(s)).toBe(normName(s));
    }
  });
});

// --- 3. Corpus parity against real upstream rows --------------------------------------

describe('nameKey — parity with the real index', () => {
  it('reproduces name_key from label for every row the collector published', () => {
    // The invariant that makes this port testable against data the upstream actually emitted,
    // rather than against my reading of its algorithm.
    const mismatches = index.products
      .map((p) => ({ label: p.label, expected: p.name_key, got: nameKey(p.label) }))
      .filter((r) => r.got !== r.expected);
    expect(mismatches).toEqual([]);
  });

  it('covers the families that actually diverge, so the check above is not vacuous', () => {
    const labels = index.products.map((p) => p.label);
    expect(labels.some((l) => /['’]/.test(l))).toBe(true); // apostrophes
    expect(labels.some((l) => /[äöüßÄÖÜ]/.test(l))).toBe(true); // umlauts
    expect(labels.some((l) => /[^\w\s]/.test(l))).toBe(true); // punctuation
    expect(index.products.length).toBeGreaterThan(30);
  });
});
