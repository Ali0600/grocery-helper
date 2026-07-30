import { DEFAULT_PLZ } from '../config';
import { MAX_INDEX_BYTES, isCoveredPlz } from '../usePriceHistory';

describe('price-history coverage guard', () => {
  it('covers Berlin and nothing else', () => {
    // The collector's only region is `berlin`. Outside it every lookup would miss, so the
    // download is skipped rather than spent — and a Hamburg user is never shown Berlin's
    // price history.
    expect(isCoveredPlz('10115')).toBe(true); // Mitte
    expect(isCoveredPlz('14199')).toBe(true); // the upper edge
    expect(isCoveredPlz('10114')).toBe(false);
    expect(isCoveredPlz('14200')).toBe(false);
    expect(isCoveredPlz('20095')).toBe(false); // Hamburg
  });

  it('rejects junk rather than coercing it', () => {
    expect(isCoveredPlz('')).toBe(false);
    expect(isCoveredPlz('abc')).toBe(false);
    expect(isCoveredPlz('10115.5')).toBe(false);
  });

  it('THE DEFAULT PLZ IS COVERED — otherwise the feature is dead on a fresh install', () => {
    // The bug this pins: the stored PLZ is only written once the user changes it, so `null`
    // is the normal first-run state. The hook falls back to DEFAULT_PLZ; if that default
    // ever moved outside the collector's region, the price trail would silently never load
    // for anyone who had not touched the location pin — and every unit test would still pass.
    expect(isCoveredPlz(DEFAULT_PLZ)).toBe(true);
  });

  it('caps the index size below the point where JSON.parse is the problem', () => {
    // A tripwire, not a precise bound: the index grows ~1,300 products/week at ~419 B each,
    // so this compressed ceiling lands around the week-26 mark — when the upstream
    // `weeks_seen >= 2` index (412 rows today, ~170 KB) stops being optional.
    expect(MAX_INDEX_BYTES).toBeGreaterThan(500_000); // today's index is ~418 KB gzipped
    expect(MAX_INDEX_BYTES).toBeLessThan(5_000_000);
  });
});
