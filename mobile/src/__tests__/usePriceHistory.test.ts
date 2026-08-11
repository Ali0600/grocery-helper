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

  it('caps the index size where the tripwire can still actually trip', () => {
    // Retuned 2026-08-11 with the switch to `index-min.json`. The old 2.5 MB ceiling was set
    // against the full index; measured against the filtered one it was ~38x the real body,
    // i.e. a tripwire wired to nothing — the thing it was meant to catch could no longer
    // reach it. That is the failure mode this test now guards.
    //
    // Measured: the filtered index is 389 KB raw / 65 KB gzipped (882 of 8,856 products
    // after 7 weeks). It only gains a product when one is seen a SECOND time, so it grows
    // far slower than the full index ever did.
    const MEASURED_GZIP = 65_259;
    expect(MAX_INDEX_BYTES).toBeGreaterThan(MEASURED_GZIP * 3); // room to grow
    expect(MAX_INDEX_BYTES).toBeLessThan(MEASURED_GZIP * 20); // ...but still reachable
  });
});
