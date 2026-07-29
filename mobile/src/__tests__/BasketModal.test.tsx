// The Basket's add list used to be a hardcoded 79-item catalog that never looked at the
// offers, so a product like Kohlrabi could not be added at all. It now also offers every
// product sub-group actually in this week's flyers — resolved through the SAME
// `subGroupItem` the swipe uses, so one product can never occupy two basket rows.
//
// RNTL v14: `render` AND `fireEvent` are both async — await both. An unawaited press opens
// overlapping act() scopes and the state update is silently DROPPED.
import { render, screen, fireEvent } from '@testing-library/react-native';
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
async function renderBasket(offers: Offer[], basket: BasketItem[] = []) {
  const onChangeBasket = jest.fn();
  const utils = await render(
    <BasketModal
      visible
      offers={offers}
      basket={basket}
      onChangeBasket={onChangeBasket}
      onClose={jest.fn()}
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
