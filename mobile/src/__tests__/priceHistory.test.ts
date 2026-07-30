/**
 * Price-trail tests, against a fixture cut from the REAL collector index — one product per
 * tier plus the two edge cases that make the tiering worth having (a flat series and a
 * `name_key` that collapsed pack variants).
 *
 * The governing measurement: 93.75% of the collector's 6,588 products have exactly one
 * data point. Tier 0 rendering NOTHING is the feature, not an omission, so it is asserted
 * first and hardest.
 */
import rawIndex from './fixtures/priceIndex.json';

import {
  MAX_POINTS,
  NOISE_RATIO,
  PriceFacts,
  buildTrail,
  joinHistory,
  projectIndex,
  trailFor,
} from '../priceHistory';
import { HistoryItem } from '../types';

const item = (name: string, chain: string): HistoryItem => ({
  key: name.toLowerCase(),
  name,
  brand: null,
  group: null,
  groupLabel: null,
  chain,
  addedPriceCents: 100,
  addedAt: Date.now(),
});

const KEYS = [
  '6io ingwer',
  'pepsi',
  'nektarinen',
  'gouda',
  'coca cola',
  'plattpfirsiche',
  'absent product',
];
const project = () => projectIndex(rawIndex, KEYS);

// --- projection ---------------------------------------------------------------------

describe('projectIndex', () => {
  it('keeps only the requested keys and records the rest as MISSES', () => {
    // `misses` is not optional: without it there is no way to distinguish "the index does
    // not have this" from "we never looked", so 94% of rows would refetch forever.
    const { byKey, misses } = project();
    expect(Object.keys(byKey).sort()).toEqual([
      '6io ingwer',
      'coca cola',
      'gouda',
      'nektarinen',
      'pepsi',
      'plattpfirsiche',
    ]);
    expect(misses).toEqual(['absent product']);
  });

  it('groups every chain that carries the same product under one key', () => {
    const { byKey } = project();
    expect(byKey['plattpfirsiche'].map((f) => f.chain).sort()).toEqual(['lidl', 'rewe']);
  });

  it('survives a malformed index instead of throwing', () => {
    // The index is fetched from a third-party host; a bad shape must degrade, not crash.
    expect(projectIndex(null, ['x']).misses).toEqual(['x']);
    expect(projectIndex({ products: 'nope' }, ['x']).byKey).toEqual({});
    expect(projectIndex({ products: [{ name_key: 'x' }] }, ['x']).byKey).toEqual({});
  });

  it('takes min/median/max from the source stats, never from the capped series', () => {
    // The cap is a storage budget. If stats were recomputed from a truncated series,
    // "cheapest ever" would silently become "cheapest recently" — the whole point of the
    // low-price line would be a lie.
    const long = {
      products: [
        {
          chain: 'lidl',
          name_key: 'long',
          label: 'Long',
          // 12 points; the 99 (the true low) is OUTSIDE the newest MAX_POINTS window
          series: Array.from({ length: 12 }, (_, i) => [`2026-W${10 + i}`, i === 0 ? 99 : 500, null]),
          stats: { min: 99, median: 500, max: 500, last: 500, weeks_seen: 12 },
          verdict: 'typical',
        },
      ],
    };
    const facts = projectIndex(long, ['long']).byKey['long'][0];
    expect(facts.series).toHaveLength(MAX_POINTS);
    expect(facts.series.some((p) => p.cents === 99)).toBe(false); // truncated away
    expect(facts.min).toBe(99); // but still reported
    expect(facts.weeksSeen).toBe(12); // not series.length
  });
});

// --- the join -----------------------------------------------------------------------

describe('joinHistory', () => {
  it('prefers the item’s own chain', () => {
    const { byKey } = project();
    const joined = joinHistory(item('Plattpfirsiche', 'rewe'), byKey);
    expect(joined?.facts.chain).toBe('rewe');
    expect(joined?.crossChain).toBe(false);
  });

  it('falls back to another chain and FLAGS it, so the row can say whose history it is', () => {
    const { byKey } = project();
    const joined = joinHistory(item('Plattpfirsiche', 'edeka'), byKey); // edeka has none
    expect(joined?.crossChain).toBe(true);
    expect(['lidl', 'rewe']).toContain(joined?.facts.chain);
  });

  it('returns null when nothing matches', () => {
    expect(joinHistory(item('Nothing At All', 'lidl'), project().byKey)).toBeNull();
  });

  it('matches through nameKey, not the app’s own normName', () => {
    // nameKey and normName disagree on ~4% of names (apostrophes/accents). The index is
    // keyed by nameKey, so the join must use it.
    const { byKey } = project();
    expect(joinHistory(item('6IO  Ingwer', 'aldi'), byKey)?.facts.chain).toBe('aldi');
  });
});

// --- the tiers ----------------------------------------------------------------------

describe('buildTrail — tiered by evidence', () => {
  it('tier 0: renders NOTHING when there is no history', () => {
    // 94% of rows land here. A "no history yet" placeholder on 94% of rows teaches the
    // user the feature is broken; the row is already complete without it.
    expect(buildTrail(null)).toEqual({ tier: 0 });
    expect(trailFor(item('Nothing At All', 'lidl'), project().byKey)).toEqual({ tier: 0 });
  });

  it('tier 1: one observation is stated, with no delta, verdict or chart', () => {
    const t = trailFor(item('6io Ingwer', 'aldi'), project().byKey);
    expect(t.tier).toBe(1);
    if (t.tier !== 1) throw new Error('unreachable');
    expect(t.cents).toBe(49);
    expect(t.week).toBe('W30'); // year stripped for the card
  });

  it('tier 2: two observations give a signed delta', () => {
    const t = trailFor(item('Pepsi', 'lidl'), project().byKey);
    expect(t.tier).toBe(2);
    if (t.tier !== 2) throw new Error('unreachable');
    expect(t.weeksSeen).toBe(2);
    expect(t.deltaPct).toBe(Math.round(((t.lastCents - t.firstCents) / t.firstCents) * 100));
  });

  it('tier 3: three or more gives stats, a verdict and a series to draw', () => {
    const t = trailFor(item('Nektarinen', 'lidl'), project().byKey, 199);
    expect(t.tier).toBe(3);
    if (t.tier !== 3) throw new Error('unreachable');
    expect(t.weeksSeen).toBe(3);
    expect([t.min, t.median, t.max]).toEqual([149, 175, 249]);
    expect(t.verdict).toBe('worse');
    expect(t.flat).toBe(false);
    expect(t.noisy).toBe(false);
    expect(t.todayPctOfUsual).toBe(Math.round((199 / 175) * 100)); // from the LIVE price
  });

  it('tier 3 FLAT: a price that never moved reports "always", not a vacuous low-vs-usual', () => {
    // edeka_center Gouda is 69 cents in all five weeks. "low 0,69 € · usual 0,69 €" is
    // noise; the honest statement is that it has never changed.
    const t = trailFor(item('Gouda', 'edeka_center'), project().byKey);
    if (t.tier !== 3) throw new Error('expected tier 3');
    expect(t.flat).toBe(true);
    expect([t.min, t.max]).toEqual([69, 69]);
  });

  it('tier 3 NOISY: a collapsed name_key suppresses the stats it would misstate', () => {
    // `coca cola` at edeka_center runs 399·69·149·1169·799 — can vs bottle vs crate, all
    // under one name_key. Reporting "usual 3,99 €" would be a number nobody can act on.
    const t = trailFor(item('Coca-Cola', 'edeka_center'), project().byKey, 500);
    if (t.tier !== 3) throw new Error('expected tier 3');
    expect(t.max / t.min).toBeGreaterThanOrEqual(NOISE_RATIO);
    expect(t.noisy).toBe(true);
    expect(t.verdict).toBeNull(); // suppressed even though the index says "worse"
    expect(t.todayPctOfUsual).toBeNull(); // a % of a meaningless median is meaningless
    expect(t.series.length).toBeGreaterThan(1); // the sparkline still renders
  });

  it('never claims a low-price WEEK the capped window cannot support', () => {
    const facts: PriceFacts = {
      chain: 'lidl',
      label: 'X',
      series: [
        { week: '2026-W30', cents: 500, unitCents: null },
        { week: '2026-W31', cents: 500, unitCents: null },
        { week: '2026-W32', cents: 500, unitCents: null },
      ],
      weeksSeen: 9,
      min: 99, // the all-time low is outside the kept window
      median: 500,
      max: 500,
      last: 500,
      verdict: 'typical',
    };
    const t = buildTrail({ facts, crossChain: false });
    if (t.tier !== 3) throw new Error('expected tier 3');
    expect(t.min).toBe(99);
    expect(t.minWeek).toBeNull(); // we do not know which week it was
  });

  it('suppresses a "new" verdict — it means "not enough weeks", not a judgement', () => {
    const { byKey } = project();
    const t = buildTrail(joinHistory(item('Plattpfirsiche', 'lidl'), byKey));
    if (t.tier !== 3) throw new Error('expected tier 3');
    expect(t.verdict).toBe('true_low'); // this one IS a judgement
    const asNew = buildTrail({
      facts: { ...byKey['plattpfirsiche'][0], verdict: 'new' },
      crossChain: false,
    });
    if (asNew.tier !== 3) throw new Error('expected tier 3');
    expect(asNew.verdict).toBeNull();
  });

  it('carries the collector’s own label, so a bad name_key collapse is auditable', () => {
    const t = trailFor(item('Coca-Cola', 'edeka_center'), project().byKey);
    if (t.tier !== 3) throw new Error('expected tier 3');
    expect(t.label).toBe('Coca-Cola');
  });
});
