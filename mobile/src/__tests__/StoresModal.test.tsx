// The Stores modal is where "my stores" is chosen, and it now drives which chains' deals
// appear (rather than being a decorative bookmark), so its Add/Added state is real
// behaviour worth pinning — above all the default the user expected: a chain we track
// reads as "Added ✓" without them having to do anything.

import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import React from 'react';
import { Dimensions } from 'react-native';

import { StoresModal } from '../components/StoresModal';
import { CHAIN_ORDER } from '../dealFilters';
import { NearbyStore } from '../types';

jest.mock('../api', () => ({
  api: {
    base: 'http://test',
    nearbyStores: jest.fn(),
    chainBranches: jest.fn(),
    flyerPages: jest.fn(),
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
  api.flyerPages.mockResolvedValue({});
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

describe('the flyer viewer', () => {
  // Derived, not guessed: the view lays each page out at the window width minus the
  // sheet's 1px borders, and a hardcoded number here would silently stop landing on a
  // page boundary if that changed.
  const PAGE_W = Math.max(1, Math.round(Dimensions.get('window').width) - 2);
  const PAGES = ['p0.jpg', 'p1.jpg', 'p2.jpg', 'p3.jpg', 'p4.jpg', 'p5.jpg', 'p6.jpg', 'p7.jpg'];

  it('offers "View flyer" only for chains the backend actually captured pages for', async () => {
    api.flyerPages.mockResolvedValue({ lidl: PAGES, rewe: ['r0.jpg'] });
    await setup();

    expect(await screen.findByLabelText('View lidl flyer')).toBeTruthy();
    expect(screen.getByLabelText('View rewe flyer')).toBeTruthy();
    // Absent from the map = no link, which is how dm (no brochure, ever) and any chain
    // whose scrape failed are handled without naming either of them in the app.
    expect(screen.queryByLabelText('View edeka flyer')).toBeNull();
    expect(screen.queryByLabelText('View Netto flyer')).toBeNull();
  });

  it('shows only the first FLYER_PAGE_CAP pages of a longer flyer', async () => {
    api.flyerPages.mockResolvedValue({ lidl: PAGES });
    await setup();
    await fireEvent.press(await screen.findByLabelText('View lidl flyer'));

    // Assert the COUNTER, not the number of rendered <Image>s: under jest a FlatList
    // renders its whole initial window, so counting testIDs would pass even uncapped.
    expect(await screen.findByText('1 / 5')).toBeTruthy();
  });

  it('advances the page counter as the flyer is paged', async () => {
    // Regression for a WEB-ONLY defect: react-native-web accepts `onMomentumScrollEnd` and
    // never calls it (the DOM has no momentum-end event), so the counter sat frozen at
    // "1 / 5" while the pages turned. `onScroll` fires on both platforms.
    api.flyerPages.mockResolvedValue({ lidl: PAGES });
    await setup();
    await fireEvent.press(await screen.findByLabelText('View lidl flyer'));
    expect(await screen.findByText('1 / 5')).toBeTruthy();

    const pager = screen.getByTestId('flyer-pager');
    await fireEvent.scroll(pager, {
      nativeEvent: {
        contentOffset: { x: 2 * PAGE_W, y: 0 },
        contentSize: { width: 5 * PAGE_W, height: 400 },
        layoutMeasurement: { width: PAGE_W, height: 400 },
      },
    });

    expect(await screen.findByText('3 / 5')).toBeTruthy();
  });

  it('goes back to the store list', async () => {
    api.flyerPages.mockResolvedValue({ lidl: PAGES });
    await setup();
    await fireEvent.press(await screen.findByLabelText('View lidl flyer'));
    expect(screen.queryByText('Deals coming soon')).toBeNull();

    await fireEvent.press(screen.getByLabelText('Back to stores'));

    expect(await screen.findByText('Deals coming soon')).toBeTruthy();
  });

  it('serves a fresh cached map without calling the backend', async () => {
    // Flyers are weekly, like the deals — a mid-week open must not spend a round trip
    // (and on the free tier, possibly a cold start) re-fetching an unchanged booklet.
    await AsyncStorage.setItem(
      'flyerPagesCache',
      JSON.stringify({ plz: '10115', byChain: { lidl: PAGES }, cachedAt: Date.now() }),
    );

    await setup();

    expect(await screen.findByLabelText('View lidl flyer')).toBeTruthy();
    expect(api.flyerPages).not.toHaveBeenCalled();
  });

  it('keeps the stores list when the flyer endpoint fails', async () => {
    // An older backend 404s here. That may cost the links; it must not cost the list.
    api.flyerPages.mockRejectedValue(new Error('API 404'));

    await setup();

    expect(screen.getByText('Deals coming soon')).toBeTruthy();
    await waitFor(() => expect(screen.queryByLabelText('View lidl flyer')).toBeNull());
  });
});
