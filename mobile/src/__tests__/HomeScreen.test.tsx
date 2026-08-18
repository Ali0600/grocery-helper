// The landing screen. Its job is small but load-bearing: it's the only way into any
// vertical, and the deal count it shows must come from that vertical's OWN cache.

import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, render, screen } from '@testing-library/react-native';
import React from 'react';

import HomeScreen from '../screens/HomeScreen';
import { setDealsCache } from '../storage';
import { VERTICALS, VERTICAL_LABELS } from '../verticals';
import { makeOffer } from './fixtures';

const cached = (names: string[]) => ({
  plz: '10115',
  offers: names.map((name) => makeOffer({ name })),
  cats: [],
  storeName: 'Test',
  cachedAt: Date.now(),
});

describe('HomeScreen', () => {
  it('offers every vertical, in the registry’s own order', async () => {
    await render(<HomeScreen onPick={() => {}} />);
    // Driven off VERTICALS rather than a list of names: this screen is the ONLY way into a
    // section, so a section added to the registry and not rendered here is unreachable —
    // and a test naming the sections it expects would go on passing.
    for (const v of VERTICALS) expect(screen.getByTestId(`vertical-${v}`)).toBeTruthy();
    expect(VERTICALS).toEqual(['grocery', 'drinks', 'drugstore']);
  });

  it('reports which vertical was picked', async () => {
    const onPick = jest.fn();
    await render(<HomeScreen onPick={onPick} />);
    await fireEvent.press(screen.getByTestId('vertical-drugstore'));
    expect(onPick).toHaveBeenCalledWith('drugstore');
  });

  it('shows each vertical’s OWN cached deal count', async () => {
    await setDealsCache('grocery', cached(['a', 'b', 'c']));
    await setDealsCache('drinks', cached(['beer', 'cola']));
    await setDealsCache('drugstore', cached(['x']));
    await render(<HomeScreen onPick={() => {}} />);

    // Sabotage check: read one shared cache and every card reports the same number. Three
    // distinct counts is what makes that impossible to pass by accident.
    expect(await screen.findByLabelText('Grocery, 3 deals')).toBeTruthy();
    expect(screen.getByLabelText('Drinks, 2 deals')).toBeTruthy();
    expect(screen.getByLabelText('Drugstore, 1 deals')).toBeTruthy();
  });

  it('labels every vertical, so a new one can’t render as blank', async () => {
    await render(<HomeScreen onPick={() => {}} />);
    // VERTICAL_LABELS/_BLURBS/_ICONS are `Record<Vertical, …>`, so tsc catches a missing
    // key — but only if the screen reads all three, which is what this checks at runtime.
    for (const v of VERTICALS) {
      expect(await screen.findByText(VERTICAL_LABELS[v])).toBeTruthy();
    }
  });

  it('falls back to a blurb when a vertical has no cache yet', async () => {
    await AsyncStorage.clear();
    await render(<HomeScreen onPick={() => {}} />);
    // A fresh install must not render "0 deals" — that reads as "this section is empty"
    // when it only means "never opened".
    expect(await screen.findByLabelText('Grocery, Supermarket flyer deals')).toBeTruthy();
    expect(screen.queryByLabelText('Grocery, 0 deals')).toBeNull();
  });
});
