// The Basket's add list used to be a hardcoded 79-item catalog that never looked at the
// offers, so a product like Kohlrabi could not be added at all. It now also offers every
// product sub-group actually in this week's flyers — resolved through the SAME
// `subGroupItem` the swipe uses, so one product can never occupy two basket rows.
//
// RNTL v14: `render` AND `fireEvent` are both async — await both. An unawaited press opens
// overlapping act() scopes and the state update is silently DROPPED.
import { render, screen, fireEvent, within } from '@testing-library/react-native';
import React from 'react';

import { resolveBasketItem, subGroupItem } from '../basketResolve';
import { BasketModal } from '../components/BasketModal';
import { BasketItem, Offer } from '../types';
import { makeOffer } from './fixtures';

const kohlrabi = makeOffer({
  id: 901,
  name: 'Kohlrabi',
  group: 'kohlrabi',
  group_label: 'Kohlrabi',
  category: 'vegetables',
  category_label: 'Vegetables',
  price_cents: 79,
});
// A sub-group that DOES have a catalog counterpart (catalog "Bell pepper" / de "Paprika").
const paprika = makeOffer({
  id: 902,
  name: 'Spitzpaprika rot',
  group: 'paprika',
  group_label: 'Paprika',
  category: 'vegetables',
  category_label: 'Vegetables',
  price_cents: 149,
});

// `render` is async in RNTL v14, so it must be AWAITED here — spreading the Promise
// leaves `screen` unbound and every assertion fails with "render function has not been
// called", far away from the actual mistake.
async function renderBasket(offers: Offer[], basket: BasketItem[] = [], storeLens: string[] = []) {
  const onChangeBasket = jest.fn();
  const utils = await render(
    <BasketModal
      visible
      offers={offers}
      basket={basket}
      onChangeBasket={onChangeBasket}
      onClose={jest.fn()}
      storeLens={storeLens}
    />,
  );
  return { onChangeBasket, ...utils };
}

describe('BasketModal — sub-groups from this week’s flyers', () => {
  it('offers a sub-group the curated catalog does not have', async () => {
    await renderBasket([kohlrabi]);
    expect(screen.getByLabelText('Add Kohlrabi to basket')).toBeTruthy();
  });

  it('shows a catalog-mapped sub-group once, under its catalog label', async () => {
    await renderBasket([paprika]);
    // "Paprika" resolves to the catalog `pepper` item, so it must render as the catalog
    // chip "Bell pepper" and NOT a second time as a German "Paprika" chip.
    expect(screen.queryByLabelText('Add Paprika to basket')).toBeNull();
    expect(screen.getAllByLabelText('Add Bell pepper to basket')).toHaveLength(1);
  });

  it('adds the SAME basket key a swipe on that deal would', async () => {
    // The whole point of the shared seam: derive the expectation from resolveBasketItem
    // rather than hardcoding 'grp:kohlrabi', so this fails on drift, not on a rename.
    const { onChangeBasket } = await renderBasket([kohlrabi]);
    await fireEvent.press(screen.getByLabelText('Add Kohlrabi to basket'));
    expect(onChangeBasket).toHaveBeenCalledWith([resolveBasketItem(kohlrabi)]);
  });

  it('drops a sub-group that is already in the basket', async () => {
    // The pre-existing "already in basket" filter is written against GROCERY_CATALOG, so
    // the live list needs its own — and it must compare RESOLVED keys.
    await renderBasket([kohlrabi], [subGroupItem('kohlrabi', 'Kohlrabi')]);
    expect(screen.queryByLabelText('Add Kohlrabi to basket')).toBeNull();
  });

  it('finds a live sub-group by its German name', async () => {
    await renderBasket([kohlrabi]);
    await fireEvent.changeText(screen.getByPlaceholderText(/Add an item/), 'kohl');
    expect(screen.getByLabelText('Add Kohlrabi to basket')).toBeTruthy();
  });

  it('still shows the popular staples when the box is empty', async () => {
    // Regression guard: the live section must not displace the curated default view.
    await renderBasket([kohlrabi]);
    expect(screen.getByLabelText('Add Milk to basket')).toBeTruthy();
  });

  it('reaches the late-alphabet categories, not just the first few', async () => {
    // Found in web QA, not by these tests: the chips are ordered by category name, so a cap
    // small enough to bite truncates ALPHABETICALLY — 30 slots went to Bakery→Fish and
    // Vegetables (the whole point of the feature) never rendered. The earlier fixtures used
    // one category each, so the cap could never bite. Span the alphabet instead.
    const spread = [
      'Bakery', 'Beef', 'Cheese', 'Chicken & Poultry', 'Coffee', 'Fish & Seafood',
      'Milk & Dairy', 'Pork & Sausage', 'Snacks', 'Soft Drinks', 'Vegetables',
    ].flatMap((categoryLabel, ci) =>
      Array.from({ length: 5 }, (_, i) =>
        makeOffer({
          id: 1000 + ci * 10 + i,
          name: `${categoryLabel} product ${i}`,
          group: `g${ci}-${i}`,
          group_label: `Group ${ci}-${i}`,
          category: categoryLabel.toLowerCase(),
          category_label: categoryLabel,
        }),
      ),
    );
    await renderBasket([...spread, kohlrabi]);
    expect(screen.getByLabelText('Add Kohlrabi to basket')).toBeTruthy();
  });

  it('never suggests a household sub-group', async () => {
    // The basket is a grocery list; BasketModal drops household before matching, and the
    // suggestions must inherit that or they reintroduce the Birne→Glühbirne trap.
    const bags = makeOffer({
      id: 903,
      name: 'Müllbeutel',
      group: 'muellbeutel',
      group_label: 'Müllbeutel',
      category: 'household',
      category_label: 'Household',
    });
    await renderBasket([bags]);
    expect(screen.queryByLabelText('Add Müllbeutel to basket')).toBeNull();
  });
});

// The deals list's "Only show" lens now scopes the plan: if you've said you're shopping Lidl
// and Aldi, a plan built from every chain isn't a plan you can act on. It scopes MATCHING
// only — what you can add stays the full week's vocabulary (see the last two cases).
describe('BasketModal — the store lens scopes the plan', () => {
  const MILK = { key: 'milk', label: 'Milk', keywords: ['milch'] };
  const BUTTER = { key: 'butter', label: 'Butter', keywords: ['butter'] };

  const lidlMilk = makeOffer({
    id: 910,
    chain: 'lidl',
    name: 'Milbona Frische Vollmilch',
    category: 'dairy',
    price_cents: 129,
  });
  // Cheaper, so an unlensed plan prefers it — which is what makes the lens test meaningful.
  const reweMilk = makeOffer({
    id: 911,
    chain: 'rewe',
    name: 'REWE Bio Vollmilch',
    category: 'dairy',
    price_cents: 99,
  });
  const edekaButter = makeOffer({
    id: 912,
    chain: 'edeka',
    name: 'Gut&Günstig Deutsche Markenbutter',
    category: 'butter',
    price_cents: 189,
  });
  // Only at REWE — so a Lidl lens excludes it from matching (but must not un-add it).
  const reweKohlrabi = makeOffer({ ...kohlrabi, id: 913, chain: 'rewe' });
  const all = [lidlMilk, reweMilk, edekaButter];

  it('matches inside the lens, not just displays it', async () => {
    // The load-bearing assertion: unlensed this plan would pick REWE at 0,99 €. Lensed to
    // Lidl it must take the PRICIER Lidl milk — proving the lens reaches buildPlan's input
    // rather than merely hiding a row.
    await renderBasket(all, [MILK], ['lidl']);
    const plan = screen.getByTestId('plan-card');
    expect(within(plan).getByText('Milbona Frische Vollmilch')).toBeTruthy();
    expect(screen.queryByText('REWE Bio Vollmilch')).toBeNull();
  });

  it('says the plan is narrowed, so a hidden cheaper store does not read as a missing deal', async () => {
    await renderBasket(all, [MILK], ['lidl', 'edeka']);
    expect(within(screen.getByTestId('plan-card')).getByText('Only Lidl · Edeka')).toBeTruthy();
  });

  // Separate test, not a second half of the one above: a manual unmount() leaves `screen`
  // bound to the dead tree and every later assertion in the file fails somewhere else.
  it('shows no lens note when nothing is lensed', async () => {
    await renderBasket(all, [MILK]);
    expect(within(screen.getByTestId('plan-card')).queryByText(/^Only /)).toBeNull();
  });

  it('lists each item with its price and matched product, not a bare count', async () => {
    await renderBasket(all, [MILK, BUTTER]);
    const plan = screen.getByTestId('plan-card');
    expect(within(plan).getByText('Milk')).toBeTruthy();
    // Twice: once as REWE's subtotal, once as the milk line under it (one item per store, so
    // they're equal). The second occurrence IS the item line — one match means it's missing.
    expect(within(plan).getAllByText('0,99 €')).toHaveLength(2);
    expect(within(plan).getByText('REWE Bio Vollmilch')).toBeTruthy();
    expect(within(plan).getByText('Butter')).toBeTruthy();
    expect(within(plan).getByText('Gut&Günstig Deutsche Markenbutter')).toBeTruthy();
    // The old "N items" summary is gone — the items themselves replaced it.
    expect(within(plan).queryByText(/\d+ items?$/)).toBeNull();
  });

  it('reports an item with no in-lens deal as missing rather than dropping it', async () => {
    await renderBasket(all, [MILK, BUTTER], ['lidl']);
    expect(within(screen.getByTestId('plan-card')).getByText(/No deal this week: Butter/)).toBeTruthy();
  });

  it('does NOT lens what you can add — a basket item is store-agnostic', async () => {
    // Kohlrabi is only at REWE while the lens is Lidl. It must still be addable: you're
    // saying "I want kohlrabi", and the plan will honestly report no in-lens deal.
    await renderBasket([lidlMilk, reweKohlrabi], [], ['lidl']);
    expect(screen.getByLabelText('Add Kohlrabi to basket')).toBeTruthy();
  });

  it('keys a typed add off the live groups even when the lens excludes them', async () => {
    // The invariant this protects: `addFromText` falls through the live groups before minting
    // a `free:` key. Lensing that path would make typing "Kohlrabi" and swiping the same deal
    // mint DIFFERENT keys, putting one product in the basket twice.
    const { onChangeBasket } = await renderBasket([lidlMilk, reweKohlrabi], [], ['lidl']);
    await fireEvent.changeText(screen.getByPlaceholderText(/Add an item/), 'Kohlrabi');
    await fireEvent(screen.getByPlaceholderText(/Add an item/), 'submitEditing');
    expect(onChangeBasket).toHaveBeenCalledWith([resolveBasketItem(kohlrabi)]);
  });
});
