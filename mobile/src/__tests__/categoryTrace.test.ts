// The pure half of "Why this category?" — reading a classifier trace.
//
// The counterfactual logic is the part worth pinning: "which layers decided but lost" is
// what turns a trace from trivia into "here's where the fix goes", and it's easy to get
// subtly wrong (include the winner, or include earlier layers).
import {
  counterfactuals,
  LAYER_LABELS,
  layerLabel,
  reasonLabel,
  ruleAddress,
  verdictDetail,
  winningLayer,
} from '../categoryTrace';
import { CategoryTrace, TraceLayer } from '../types';

const L = (over: Partial<TraceLayer> & { layer: string }): TraceLayer => ({
  status: 'no_match',
  ...over,
});

// The real shape for "Radeberger Premium-Lachsschinken" under a Fisch > Lachs path:
// layer 2 wins with pork, and layer 3's path would have said fish.
const lachsschinken: CategoryTrace = {
  category: 'pork',
  inputs: { category_path: ['Lebensmittel und Getränke', 'Fisch', 'Lachs'] },
  layers: [
    L({ layer: '0' }),
    L({ layer: '1', status: 'skipped', reason: 'path_is_food_root' }),
    L({
      layer: '2', status: 'decided', slug: 'pork', table: '_FORM_OVERRIDES',
      index: 10, matched: 'lachsschinken', where: 'name_text',
    }),
    L({ layer: '2b', status: 'skipped', reason: 'no_unit' }),
    L({ layer: '3', status: 'decided', slug: 'fish', table: '_PATH_MAP', matched: 'Lachs' }),
    L({ layer: '4' }),
    L({ layer: '5' }),
    L({ layer: '6', status: 'decided', slug: 'fish', table: '_RULES', index: 3, matched: 'lachs' }),
    L({ layer: '7', status: 'decided', slug: 'other', reason: 'fallback' }),
  ],
};

describe('winningLayer', () => {
  it('is the FIRST layer that decided, matching the backend cascade', () => {
    expect(winningLayer(lachsschinken)?.layer).toBe('2');
  });
});

describe('counterfactuals', () => {
  it('lists the layers that decided but lost — never the winner, never earlier layers', () => {
    expect(counterfactuals(lachsschinken).map((l) => [l.layer, l.slug])).toEqual([
      ['3', 'fish'],
      ['6', 'fish'],
      ['7', 'other'],
    ]);
  });

  it('is empty when the winner is the last decided layer', () => {
    const onlyFallback: CategoryTrace = {
      category: 'other',
      inputs: {},
      layers: [L({ layer: '6' }), L({ layer: '7', status: 'decided', slug: 'other' })],
    };
    expect(counterfactuals(onlyFallback)).toEqual([]);
  });
});

describe('verdictDetail', () => {
  it('quotes the matched token', () => {
    expect(verdictDetail(lachsschinken.layers[2])).toBe('"lachsschinken"');
  });

  it('says when a brand matched the brand COLUMN rather than the product name', () => {
    const brand = L({
      layer: '4', status: 'decided', slug: 'butter', table: 'BRAND_CATEGORY',
      index: 17, matched: 'kerrygold', where: 'brand_field',
    });
    expect(verdictDetail(brand)).toBe('"kerrygold" (brand field)');
    expect(verdictDetail({ ...brand, where: 'name_text' })).toBe('"kerrygold"');
  });

  it('falls back to the reason when nothing matched (layer 1 household, the fallback)', () => {
    expect(verdictDetail(L({ layer: '1', status: 'decided', slug: 'household', reason: 'no_rescue_token' })))
      .toBe('no food word to rescue it');
  });
});

describe('ruleAddress', () => {
  it('is the editable address, since repeated slugs mean the slug names nothing', () => {
    expect(ruleAddress(lachsschinken.layers[2])).toBe('_FORM_OVERRIDES[10]');
  });

  it('omits the index for a dict lookup like _PATH_MAP, and is null with no table', () => {
    expect(ruleAddress(lachsschinken.layers[4])).toBe('_PATH_MAP');
    expect(ruleAddress(L({ layer: '7', status: 'decided', slug: 'other' }))).toBeNull();
  });
});

describe('labels', () => {
  it('names every layer the backend can emit — a gap would render "Layer 2b" as a raw id', () => {
    // Sorted, not in insertion order: JS hoists integer-like keys, so "2b" sorts last here.
    expect(Object.keys(LAYER_LABELS).sort()).toEqual(
      ['0', '1', '2', '2b', '3', '4', '5', '6', '7'].sort(),
    );
    expect(layerLabel('2b')).toBe('Flyer caption');
    expect(layerLabel('99')).toBe('Layer 99');
  });

  it('translates the backend reason vocabulary, passing unknown values through', () => {
    expect(reasonLabel('no_category_path')).toBe('no category path');
    expect(reasonLabel('rescue_veto')).toBe('a veto word blocked the food rescue');
    expect(reasonLabel(undefined)).toBeNull();
    expect(reasonLabel('brand_new_reason')).toBe('brand_new_reason');
  });
});
