// The two-button landing screen. Its job is small but load-bearing: it's the only way into
// either vertical, and the deal count it shows must come from that vertical's OWN cache.

import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, render, screen } from '@testing-library/react-native';
import React from 'react';

import HomeScreen from '../screens/HomeScreen';
import { setDealsCache } from '../storage';
import { makeOffer } from './fixtures';

const cached = (names: string[]) => ({
  plz: '10115',
  offers: names.map((name) => makeOffer({ name })),
  cats: [],
  storeName: 'Test',
  cachedAt: Date.now(),
});

describe('HomeScreen', () => {
  it('offers both verticals', async () => {
    await render(<HomeScreen onPick={() => {}} />);
    expect(screen.getByTestId('vertical-grocery')).toBeTruthy();
    expect(screen.getByTestId('vertical-drugstore')).toBeTruthy();
  });

  it('reports which vertical was picked', async () => {
    const onPick = jest.fn();
    await render(<HomeScreen onPick={onPick} />);
    await fireEvent.press(screen.getByTestId('vertical-drugstore'));
    expect(onPick).toHaveBeenCalledWith('drugstore');
  });

  it('shows each vertical’s OWN cached deal count', async () => {
    await setDealsCache('grocery', cached(['a', 'b', 'c']));
    await setDealsCache('drugstore', cached(['x']));
    await render(<HomeScreen onPick={() => {}} />);

    // Sabotage check: read one shared cache and both cards report the same number.
    expect(await screen.findByLabelText('Grocery, 3 deals')).toBeTruthy();
    expect(screen.getByLabelText('Drugstore, 1 deals')).toBeTruthy();
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
