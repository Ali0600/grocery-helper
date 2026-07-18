// The "Shop at" store scope's rendered contract. The cap-at-two rule and the replace-oldest
// behaviour are invisible at the point that depends on them — adding a sixth chain, or a third
// tap, is exactly where this silently breaks — so both are pinned here.
// RNTL v14: `render` AND `fireEvent` are async — always await both.
import { fireEvent, render, screen } from '@testing-library/react-native';
import React from 'react';

import { RecipesModal } from '../components/RecipesModal';
import { DEFAULT_RECIPE_PREFS } from '../recipes';
import { Offer, RecipePrefs } from '../types';
import { makeOffer } from './fixtures';

const noop = () => {};

// Three chains present, so the scope row renders and a third tap is reachable.
const offers: Offer[] = [
  makeOffer({ chain: 'lidl', name: 'Hähnchenbrust' }),
  makeOffer({ chain: 'rewe', name: 'Junger Gouda' }),
  makeOffer({ chain: 'edeka', name: 'Kirschen' }),
];

async function renderSheet(prefs: Partial<RecipePrefs> = {}) {
  const onChangePrefs = jest.fn();
  await render(
    <RecipesModal
      visible
      offers={offers}
      prefs={{ ...DEFAULT_RECIPE_PREFS, ...prefs }}
      onChangePrefs={onChangePrefs}
      alwaysHave={[]}
      onChangeAlwaysHave={noop}
      onClose={noop}
    />,
  );
  return onChangePrefs;
}

describe('RecipesModal — "Shop at"', () => {
  it('offers a chip per present chain, and none for an absent one', async () => {
    await renderSheet();
    expect(screen.getByLabelText('Shop at any store')).toBeTruthy();
    expect(screen.getByLabelText('Shop at Lidl')).toBeTruthy();
    expect(screen.getByLabelText('Shop at REWE')).toBeTruthy();
    // ALDI has no offers in this set, so scoping to it could only produce an empty screen.
    expect(screen.queryByLabelText('Shop at Aldi')).toBeNull();
  });

  it('scopes to a single store on tap', async () => {
    const onChangePrefs = await renderSheet();
    await fireEvent.press(screen.getByLabelText('Shop at Lidl'));
    expect(onChangePrefs).toHaveBeenCalledWith(expect.objectContaining({ stores: ['lidl'] }));
  });

  it('adds a second store, then REPLACES THE OLDEST on a third pick', async () => {
    const onChangePrefs = await renderSheet({ stores: ['lidl', 'rewe'] });
    await fireEvent.press(screen.getByLabelText('Shop at Edeka'));
    // Not ['lidl','rewe'] (tap ignored) and not a three-store scope: the oldest drops out, so
    // the chip always visibly does something.
    expect(onChangePrefs).toHaveBeenCalledWith(expect.objectContaining({ stores: ['rewe', 'edeka'] }));
  });

  it('deselects a chosen store when tapped again', async () => {
    const onChangePrefs = await renderSheet({ stores: ['lidl', 'rewe'] });
    await fireEvent.press(screen.getByLabelText('Shop at Lidl'));
    expect(onChangePrefs).toHaveBeenCalledWith(expect.objectContaining({ stores: ['rewe'] }));
  });

  it('"Any store" clears the scope', async () => {
    const onChangePrefs = await renderSheet({ stores: ['lidl'] });
    await fireEvent.press(screen.getByLabelText('Shop at any store'));
    expect(onChangePrefs).toHaveBeenCalledWith(expect.objectContaining({ stores: [] }));
  });

  it('hides the scope row when only one chain is present — nothing to choose between', async () => {
    await render(
      <RecipesModal
        visible
        offers={[makeOffer({ chain: 'lidl' })]}
        prefs={DEFAULT_RECIPE_PREFS}
        onChangePrefs={noop}
        alwaysHave={[]}
        onChangeAlwaysHave={noop}
        onClose={noop}
      />,
    );
    expect(screen.queryByLabelText('Shop at any store')).toBeNull();
  });
});
