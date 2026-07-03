import {
  hasAppDeal,
  headlineDiscountPct,
  headlinePriceCents,
  headlineStrikeCents,
} from '../appPrice';
import { compareOffers } from '../dealFilters';
import { makeOffer } from './fixtures';

describe('hasAppDeal', () => {
  it('is true only when an app price is below the flyer price', () => {
    expect(hasAppDeal(makeOffer({ price_cents: 199, app_price_cents: 149 }))).toBe(true);
    expect(hasAppDeal(makeOffer({ price_cents: 199, app_price_cents: null }))).toBe(false);
    expect(hasAppDeal(makeOffer({ price_cents: 199, app_price_cents: 199 }))).toBe(false); // equal
    expect(hasAppDeal(makeOffer({ price_cents: 199, app_price_cents: 249 }))).toBe(false); // higher
  });
});

describe('headlinePriceCents', () => {
  it('is the app price for a Mit-App deal, else the flyer price', () => {
    expect(headlinePriceCents(makeOffer({ price_cents: 222, app_price_cents: 199 }))).toBe(199);
    expect(headlinePriceCents(makeOffer({ price_cents: 222, app_price_cents: null }))).toBe(222);
  });
});

describe('headlineStrikeCents', () => {
  it('strikes the regular price when a Mit-App deal has one', () => {
    const o = makeOffer({ price_cents: 222, regular_price_cents: 399, app_price_cents: 199 });
    expect(headlineStrikeCents(o)).toBe(399);
  });

  it('strikes the flyer price when a Mit-App deal has no regular price', () => {
    const o = makeOffer({ price_cents: 499, regular_price_cents: null, app_price_cents: 379 });
    expect(headlineStrikeCents(o)).toBe(499);
  });

  it('is the regular price (or null) for a non-app offer', () => {
    expect(headlineStrikeCents(makeOffer({ price_cents: 199, regular_price_cents: 299 }))).toBe(299);
    expect(headlineStrikeCents(makeOffer({ price_cents: 199, regular_price_cents: null }))).toBe(
      null,
    );
  });
});

describe('headlineDiscountPct', () => {
  it('measures the app price against the regular price when present', () => {
    // Schöller Nuii: flyer 2,22 / reg 3,99 / app 1,99 → (399-199)/399 ≈ 50%.
    const o = makeOffer({ price_cents: 222, regular_price_cents: 399, app_price_cents: 199 });
    expect(headlineDiscountPct(o)).toBe(50);
  });

  it('measures the app price against the flyer price when there is no regular price', () => {
    // Berliner Pilsner: flyer 4,99 / app 3,79 → (499-379)/499 ≈ 24% (had no badge before).
    const o = makeOffer({ price_cents: 499, regular_price_cents: null, app_price_cents: 379 });
    expect(headlineDiscountPct(o)).toBe(24);
  });

  it('passes the stored discount_pct straight through for a non-app offer', () => {
    expect(
      headlineDiscountPct(makeOffer({ price_cents: 199, regular_price_cents: 299, discount_pct: 33.4 })),
    ).toBe(33.4);
    expect(headlineDiscountPct(makeOffer({ price_cents: 199, discount_pct: null }))).toBe(null);
  });

  it('returns null on incoherent data where the strike base is not above the app price', () => {
    // regular (1,00) below the app price (1,50): no positive discount to show.
    const o = makeOffer({ price_cents: 200, regular_price_cents: 100, app_price_cents: 150 });
    expect(headlineDiscountPct(o)).toBe(null);
  });
});

describe('compareOffers discount mode counts the Mit-App headline', () => {
  it('ranks a deeper app-price discount above a plain flyer discount', () => {
    const app = makeOffer({ price_cents: 222, regular_price_cents: 399, app_price_cents: 199 }); // ~50%
    const plain = makeOffer({ price_cents: 150, regular_price_cents: 270, discount_pct: 44 }); // 44%
    expect(compareOffers(app, plain, 'discount')).toBeLessThan(0); // app sorts first
    expect([plain, app].sort((a, b) => compareOffers(a, b, 'discount'))).toEqual([app, plain]);
  });
});
