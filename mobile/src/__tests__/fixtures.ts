// Test-only helpers. Not a suite itself: jest `testMatch` only runs *.test.ts files,
// so this module is just imported by the suites for building fixtures.

import { Offer } from '../types';

let _seq = 1;

/**
 * Build an Offer with sensible defaults; override only the fields a test cares about.
 * Each call gets a fresh `id` so picks-by-id stay unambiguous.
 */
export function makeOffer(partial: Partial<Offer> = {}): Offer {
  return {
    id: _seq++,
    store_id: 1,
    chain: 'lidl',
    store_name: 'Lidl Berlin',
    source: 'flyer',
    name: 'Test product',
    brand: null,
    category: 'other',
    category_label: 'Other',
    group: null,
    group_label: null,
    price_cents: 199,
    regular_price_cents: null,
    discount_pct: null,
    unit: null,
    price_per_unit: null,
    unit_price_cents: null,
    loyalty_note: null,
    app_price_cents: null,
    image_url: null,
    valid_from: null,
    valid_to: null,
    valid_days: null,
    day_limited: false,
    ...partial,
  };
}
