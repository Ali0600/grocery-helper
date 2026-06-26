// Unit tests for the pure display/format helpers (src/format.ts).

import { cleanUnit, dealsStale, euro, fmtPricePerUnit, formatBrand, pct, todayISO } from '../format';

describe('euro / pct', () => {
  it('formats cents as a German euro string', () => {
    expect(euro(139)).toBe('1,39 €');
    expect(euro(0)).toBe('0,00 €');
    expect(euro(2500)).toBe('25,00 €');
  });

  it('rounds a discount percent into a badge, or empty for null', () => {
    expect(pct(41.8)).toBe('-42%');
    expect(pct(20)).toBe('-20%');
    expect(pct(null)).toBe('');
  });
});

describe('cleanUnit', () => {
  it('drops purchase-limit parentheticals and a leading "Je "', () => {
    expect(cleanUnit('Je 150 g (Max. 24 Stück)')).toBe('150 g');
  });

  it('passes a per-unit fallback through unchanged, and is null-safe', () => {
    expect(cleanUnit('1 kg = 1.93')).toBe('1 kg = 1.93');
    expect(cleanUnit(null)).toBeNull();
  });
});

describe('fmtPricePerUnit', () => {
  it('formats the "1 kg = X" shape, stripping the leading "1 " and German comma', () => {
    expect(fmtPricePerUnit('1 kg = 13.33')).toBe('13,33 €/kg');
    expect(fmtPricePerUnit('100 g = 0.50')).toBe('0,50 €/100 g');
  });

  it('formats the bare "<value> €/<unit>" shape, dropping a trailing dot', () => {
    expect(fmtPricePerUnit('22.79 €/kg')).toBe('22,79 €/kg');
    expect(fmtPricePerUnit('0.46 €/Stk.')).toBe('0,46 €/Stk');
  });

  it('is null-safe and rejects garbage', () => {
    expect(fmtPricePerUnit(null)).toBeNull();
    expect(fmtPricePerUnit('not a price')).toBeNull();
  });
});

describe('formatBrand', () => {
  it('title-cases shouting brands but leaves intentionally-styled ones alone', () => {
    expect(formatBrand('EHRMANN')).toBe('Ehrmann');
    expect(formatBrand('RITTER SPORT')).toBe('Ritter Sport');
    expect(formatBrand('LIVARNO home')).toBe('LIVARNO home');
    expect(formatBrand(null)).toBeNull();
  });
});

describe('todayISO / dealsStale (weekly Sunday expiry)', () => {
  // Pin "now" to a fixed instant so the date logic is deterministic.
  const NOW = new Date('2026-06-24T12:00:00'); // local time
  const DAY = 24 * 60 * 60 * 1000;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(NOW);
  });
  afterEach(() => jest.useRealTimers());

  it('todayISO renders the device-local date', () => {
    expect(todayISO()).toBe('2026-06-24');
  });

  it('a cache from this week is fresh; from a prior week is stale', () => {
    expect(dealsStale(NOW.getTime())).toBe(false); // cached now
    expect(dealsStale(NOW.getTime() - 60 * 60 * 1000)).toBe(false); // earlier today
    expect(dealsStale(NOW.getTime() - 8 * DAY)).toBe(true); // last week, past its Sunday
    expect(dealsStale(null)).toBe(false); // no cache → not stale
  });
});
