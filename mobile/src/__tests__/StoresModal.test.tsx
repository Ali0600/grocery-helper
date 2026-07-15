// The Stores modal is where "my stores" is chosen, and it now drives which chains' deals
// appear (rather than being a decorative bookmark), so its Add/Added state is real
// behaviour worth pinning — above all the default the user expected: a chain we track
// reads as "Added ✓" without them having to do anything.

import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import React from 'react';

import { StoresModal } from '../components/StoresModal';
import { CHAIN_ORDER } from '../dealFilters';
import { NearbyStore } from '../types';

jest.mock('../api', () => ({
  api: {
    base: 'http://test',
    nearbyStores: jest.fn(),
    chainBranches: jest.fn(),
  },
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { api } = require('../api');

const store = (chain: string, label: string, over: Partial<NearbyStore> = {}): NearbyStore => ({
  chain,
  label,
  name: `${label} Musterstadt`,
  address: 'Leipziger Straße 42',
  lat: 52.5,
  lng: 13.4,
  distance_m: 200,
  active: true,
  ...over,
});

// Every tracked chain, so the modal adds no placeholder rows (it synthesises one for any
// CHAIN_ORDER chain the 2.5 km lookup missed, which would double the buttons under test).
const NEARBY: NearbyStore[] = [
  ...CHAIN_ORDER.map((c) => store(c, c === 'aldi' ? 'Aldi' : c)),
  store('netto', 'Netto', { active: false, distance_m: 838 }), // we don't scrape this one
];

const COUNTS = Object.fromEntries(CHAIN_ORDER.map((c) => [c, 100]));

// RNTL v14's `render` is ASYNC (it was sync in v13). Without the await, `screen` is still
// unbound when the test queries and every failure reads "render function has not been
// called" — which points nowhere near the real cause.
async function setup(props: Partial<React.ComponentProps<typeof StoresModal>> = {}) {
  const onToggleStore = jest.fn();
  await render(
    <StoresModal
      visible
      plz="10115"
      myStores={[]}
      onChangeMyStores={jest.fn()}
      hiddenStores={[]}
      onToggleStore={onToggleStore}
      chainCounts={{ ...COUNTS, aldi: 244 }}
      onClose={jest.fn()}
      {...props}
    />,
  );
  await screen.findByText('Deals coming soon'); // the list has rendered
  return { onToggleStore };
}

beforeEach(() => {
  jest.clearAllMocks();
  api.nearbyStores.mockResolvedValue(NEARBY);
});

describe('StoresModal — Add/Added drives deal visibility', () => {
  it('shows a tracked chain as "Added ✓" by default, with no action taken', async () => {
    // The original report: chains we already track read as "not added". `hiddenStores` is a
    // hidden-SET, so an untouched chain is visible — and must render as added.
    await setup();
    expect(screen.getByLabelText('Hide Aldi deals')).toBeTruthy();
    expect(screen.queryByLabelText('Show Aldi deals')).toBeNull();
    expect(screen.getAllByText('Added ✓')).toHaveLength(CHAIN_ORDER.length);
  });

  it('shows "+ Add" only for a chain whose deals are hidden', async () => {
    await setup({ hiddenStores: ['aldi'] });
    expect(screen.getByLabelText('Show Aldi deals')).toBeTruthy();
    expect(screen.getByText('+ Add')).toBeTruthy();
    expect(screen.getAllByText('Added ✓')).toHaveLength(CHAIN_ORDER.length - 1);
  });

  it('toggling a row asks to hide/show that chain, not to bookmark it', async () => {
    const { onToggleStore } = await setup();
    await fireEvent.press(screen.getByLabelText('Hide Aldi deals'));
    expect(onToggleStore).toHaveBeenCalledWith('aldi');
  });

  it('offers no Add on a chain we do not scrape — it has no deals to show', async () => {
    await setup();
    expect(screen.getByText('Deals coming soon')).toBeTruthy();
    expect(screen.queryByLabelText('Hide Netto deals')).toBeNull();
    expect(screen.queryByLabelText('Show Netto deals')).toBeNull();
  });
});

describe('StoresModal — deal counts answer "did adding it work?"', () => {
  it('shows the loaded deal count per tracked chain', async () => {
    await setup();
    expect(screen.getByText('244 deals')).toBeTruthy();
  });

  it('says so when a tracked chain has no deals loaded, instead of a silent "Added ✓"', async () => {
    await setup({ chainCounts: { ...COUNTS, aldi: 0 } }); // last scrape returned no ALDI
    expect(screen.getByText('No deals loaded — pull to refresh')).toBeTruthy();
  });

  it('singularises a lone deal', async () => {
    await setup({ chainCounts: { ...COUNTS, aldi: 1 } });
    expect(screen.getByText('1 deal')).toBeTruthy();
  });
});

describe('StoresModal — loading', () => {
  it('surfaces a friendly message when the locator returns nothing', async () => {
    api.nearbyStores.mockResolvedValue([]);
    await render(
      <StoresModal
        visible
        plz="10115"
        myStores={[]}
        onChangeMyStores={jest.fn()}
        hiddenStores={[]}
        onToggleStore={jest.fn()}
        chainCounts={{}}
        onClose={jest.fn()}
      />,
    );
    await waitFor(() => expect(screen.getByText(/Couldn't find nearby stores/i)).toBeTruthy());
  });
});
