// DealsScreen's cache/revalidate seam — the app's most valuable invariants, every one of
// which had a real bug at some point:
//   * the weekly-authoritative contract (a fresh cache makes ZERO backend calls),
//   * the cache version (a new chain was invisible until Sunday — the ALDI bug),
//   * never clobbering good data with an empty refresh (the poisoned-cache bug),
//   * the cold-PLZ on-demand scrape.
// The api module is mocked wholesale; storage runs against the official AsyncStorage
// in-memory mock (jest-setup.js). Time is pinned via a Date.now spy — no fake timers, so
// RNTL's async rendering behaves normally.

import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react-native';
import React from 'react';

import { DEALS_CACHE_VERSION } from '../format';
import DealsScreen from '../screens/DealsScreen';
import { makeOffer } from './fixtures';

jest.mock('../api', () => ({
  api: {
    base: 'http://test',
    offers: jest.fn(),
    categories: jest.fn(),
    stores: jest.fn(),
    scrape: jest.fn(),
    resetDb: jest.fn(),
    recategorize: jest.fn(),
    offerPayload: jest.fn(),
    offerPayloads: jest.fn(),
    nearbyStores: jest.fn(),
    chainBranches: jest.fn(),
  },
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { api } = require('../api');

const NOW = new Date('2026-06-24T12:00:00').getTime(); // a Wednesday, mid flyer week
const CACHED_OFFER = makeOffer({ name: 'Cached Bergkäse', price_cents: 299 });
const FRESH_OFFER = makeOffer({ name: 'Frisches ALDI Angebot', price_cents: 149 });

/** A promise the test resolves by hand, so "cached renders BEFORE the refresh lands" is
 * an ordered fact rather than a race. */
function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

async function seedCache(over: Partial<Record<string, unknown>> = {}) {
  await AsyncStorage.setItem('plz', '10115');
  await AsyncStorage.setItem(
    'dealsCache',
    JSON.stringify({
      plz: '10115',
      offers: [CACHED_OFFER],
      cats: [],
      storeName: 'Lidl Testkiez',
      cachedAt: NOW,
      version: DEALS_CACHE_VERSION,
      ...over,
    }),
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(Date, 'now').mockReturnValue(NOW);
  api.categories.mockResolvedValue([]);
  api.stores.mockResolvedValue([{ id: 1, chain: 'lidl', name: 'Lidl Testkiez', plz: '10115' }]);
  api.scrape.mockResolvedValue({ scraped: 1 });
  // Payload prefetch is fire-and-forget background work — resolve it quietly.
  api.offerPayloads.mockResolvedValue({});
});

afterEach(() => {
  (Date.now as jest.Mock).mockRestore?.();
});

describe('DealsScreen — the weekly-authoritative cache contract', () => {
  it('serves a fresh current-version cache with ZERO backend calls', async () => {
    await seedCache();
    await render(<DealsScreen />);

    expect(await screen.findByText('Cached Bergkäse')).toBeTruthy();
    // The whole point of the weekly cache: a mid-week open never touches the
    // (sleepy, free-tier) backend.
    expect(api.offers).not.toHaveBeenCalled();
    expect(api.scrape).not.toHaveBeenCalled();
  });

  it('treats an older cache VERSION as stale-not-absent: cached deals render instantly, a background refresh swaps in the new set', async () => {
    // The ALDI-invisibility bug as a regression test: a release that adds a chain bumps
    // DEALS_CACHE_VERSION; without this, the fresh-cache branch above skips the backend
    // and the new chain stays invisible until Sunday.
    await seedCache({ version: DEALS_CACHE_VERSION - 1 });
    const fetch = deferred<(typeof FRESH_OFFER)[]>();
    api.offers.mockReturnValue(fetch.promise);

    await render(<DealsScreen />);

    // Stale ≠ absent: the old deals must be on screen while the refresh is in flight
    // (no spinner, no cold-start block)...
    expect(await screen.findByText('Cached Bergkäse')).toBeTruthy();
    expect(api.offers).toHaveBeenCalled();

    // ...and the new set replaces them when it lands.
    fetch.resolve([FRESH_OFFER]);
    expect(await screen.findByText('Frisches ALDI Angebot')).toBeTruthy();
    await waitFor(() => expect(screen.queryByText('Cached Bergkäse')).toBeNull());
  });

  it('re-stamps the rewritten cache with the CURRENT version, so the refresh happens once, not forever', async () => {
    await seedCache({ version: DEALS_CACHE_VERSION - 1 });
    api.offers.mockResolvedValue([FRESH_OFFER]);

    await render(<DealsScreen />);
    await screen.findByText('Frisches ALDI Angebot');

    await waitFor(() => {
      const writes = (AsyncStorage.setItem as jest.Mock).mock.calls.filter(
        ([k]) => k === 'dealsCache',
      );
      expect(writes.length).toBeGreaterThan(0);
      const latest = JSON.parse(writes[writes.length - 1][1]);
      expect(latest.version).toBe(DEALS_CACHE_VERSION);
      expect(latest.offers).toHaveLength(1);
    });
  });
});

describe('DealsScreen — an empty refresh must never destroy good data', () => {
  it('keeps the deals on screen and never writes an empty cache', async () => {
    // The poisoned-cache bug: a cold Render backend returns [] (its ephemeral DB only
    // boot-scrapes the default PLZ); that emptiness must not wipe the view or the cache.
    await seedCache({ version: DEALS_CACHE_VERSION - 1 }); // force a refresh attempt
    api.offers.mockResolvedValue([]); // backend stays empty, even after the scrape
    await render(<DealsScreen />);

    expect(await screen.findByText('Cached Bergkäse')).toBeTruthy();
    // The empty read triggers the on-demand scrape, then a refetch — still empty.
    await waitFor(() => expect(api.scrape).toHaveBeenCalled());
    // The cached offer survives...
    expect(screen.getByText('Cached Bergkäse')).toBeTruthy();
    // ...and no empty offer list was ever persisted over the good cache.
    const writes = (AsyncStorage.setItem as jest.Mock).mock.calls.filter(
      ([k]) => k === 'dealsCache',
    );
    for (const [, payload] of writes) {
      expect(JSON.parse(payload).offers.length).toBeGreaterThan(0);
    }
  });
});

describe('DealsScreen — cold start on an unscraped PLZ', () => {
  it('scrapes on demand when the first read is empty, then renders the refetched deals', async () => {
    await AsyncStorage.setItem('plz', '10115'); // no deals cache at all
    api.offers.mockResolvedValueOnce([]).mockResolvedValue([FRESH_OFFER]);

    await render(<DealsScreen />);

    expect(await screen.findByText('Frisches ALDI Angebot')).toBeTruthy();
    expect(api.scrape).toHaveBeenCalledTimes(1);
    expect(api.offers.mock.calls.length).toBeGreaterThanOrEqual(2); // read → scrape → refetch
  });
});

describe('DealsScreen — the Likes heart badge', () => {
  // The badge counts liked products on sale NOW (exact name match), not the list size —
  // it's the "something you like is back on sale" signal.
  async function seedLike(over: Partial<Record<string, unknown>> = {}) {
    await AsyncStorage.setItem(
      'likedItems',
      JSON.stringify([
        {
          key: 'cached bergkäse',
          name: 'Cached Bergkäse',
          brand: null,
          group: null,
          groupLabel: null,
          chain: 'lidl',
          likedPriceCents: 299,
          likedAt: 1,
          ...over,
        },
      ]),
    );
  }

  it('shows the on-sale count when a liked product is in the current deals', async () => {
    await seedCache();
    await seedLike();
    await render(<DealsScreen />);

    await screen.findByText('Cached Bergkäse');
    expect(within(screen.getByLabelText('Likes')).getByText('1')).toBeTruthy();
  });

  it('stays badge-less when no liked product is on sale', async () => {
    await seedCache();
    await seedLike({ key: 'nicht im angebot', name: 'Nicht im Angebot' });
    await render(<DealsScreen />);

    await screen.findByText('Cached Bergkäse');
    expect(within(screen.getByLabelText('Likes')).queryByText(/\d/)).toBeNull();
  });

  it('renders the deal detail INSIDE the Likes sheet, never as a sibling of it', async () => {
    // The iOS bug this pins (measured on a simulator, 2026-07-17): RN presents a Modal from
    // `[self reactViewController]` — the first view controller up the responder chain — so two
    // SIBLING modals resolve to the same root VC and iOS refuses the second:
    //   "Attempt to present <RCTFabricModalHostViewController> on <EXRootViewController>
    //    which is already presenting <RCTFabricModalHostViewController>".
    // The detail never appeared, and RN's `_isPresented = YES` latch (set before the failed
    // present, never rolled back) then killed EVERY later deal tap for the whole session.
    // Nested, the detail mounts into the sheet's own VC view and presents from it.
    // This constraint is invisible at the point that depends on it — moving the element one
    // level up in DealsScreen silently reintroduces the bug — so assert containment.
    await seedCache();
    await seedLike();
    await render(<DealsScreen />);
    await screen.findByText('Cached Bergkäse');

    fireEvent.press(screen.getByLabelText('Likes'));
    fireEvent.press(await screen.findByLabelText('Open deal for Cached Bergkäse'));

    // "View payload" is unique to the deal detail; it must live INSIDE the Likes modal.
    const likesModal = await screen.findByTestId('likes-modal');
    await waitFor(() => expect(within(likesModal).getByText('View payload')).toBeTruthy());

    // ...and the Likes row still comes first in tree order, which is what makes the detail
    // paint on top on react-native-web (portals mount into document.body in JSX order under
    // one z-index, so DOM order — not visibility — decides). Both platforms, one layout.
    const marks = screen.getAllByText(/liked at|View payload/);
    expect(JSON.stringify(marks[0].props.children)).toContain('liked at');
    expect(JSON.stringify(marks[1].props.children)).toContain('View payload');
  });

  it('opens the deal when the liked product NAME is tapped, not just the price block', async () => {
    // The name is the obvious thing to tap and was dead: only the ~45pt price block had a
    // press handler, so "I tap it and nothing happens" had two independent causes.
    await seedCache();
    await seedLike();
    await render(<DealsScreen />);
    await screen.findByText('Cached Bergkäse');
    fireEvent.press(screen.getByLabelText('Likes'));

    // The row's pressable wraps the whole main column, name included.
    const row = await screen.findByLabelText('Open deal for Cached Bergkäse');
    expect(within(row).getByText('Cached Bergkäse')).toBeTruthy();

    fireEvent.press(row);
    expect(await screen.findByText('View payload')).toBeTruthy();
  });

  it('drops the detail when the Likes sheet closes, so it cannot change host mid-flight', async () => {
    // If `active` outlived the sheet, the single detail element would move from inside the
    // sheet to the screen root — a remount that races a dismissal against a present.
    await seedCache();
    await seedLike();
    await render(<DealsScreen />);
    await screen.findByText('Cached Bergkäse');

    fireEvent.press(screen.getByLabelText('Likes'));
    fireEvent.press(await screen.findByLabelText('Open deal for Cached Bergkäse'));
    await screen.findByText('View payload');

    // Both sheets carry a "Close" — the detail nests inside Likes — so target the labelled one.
    fireEvent.press(screen.getByLabelText('Close likes'));
    await waitFor(() => expect(screen.queryByText('View payload')).toBeNull());
  });
});

describe('DealsScreen — the header is pin-only', () => {
  it('drops the PLZ text but keeps it ANNOUNCED, so removing it visually is not an a11y regression', async () => {
    // Six icon actions + a text block don't fit a phone: the 6th icon squeezed "PLZ 10713"
    // to "P…" at 375/390pt. The pin stays; the code moves into the label.
    await seedCache();
    await render(<DealsScreen />);
    await screen.findByText('Cached Bergkäse');

    expect(screen.queryByText('PLZ 10715')).toBeNull();
    expect(screen.queryByText(/^PLZ /)).toBeNull(); // no visible postal-code text at all
    expect(screen.getByLabelText('Change postal code, currently 10115')).toBeTruthy();
  });
});

describe('DealsScreen — the "My Categories" home', () => {
  // Cache with two fruit deals + a couple of categories, so a Mine shelf and the editor have data.
  const fruitCache = () =>
    seedCache({
      offers: [
        makeOffer({ name: 'Bananen', category: 'fruits', category_label: 'Fruits', price_cents: 149 }),
        makeOffer({ name: 'Äpfel', category: 'fruits', category_label: 'Fruits', price_cents: 199 }),
      ],
      cats: [
        { category: 'fruits', label: 'Fruits', count: 2 },
        { category: 'cheese', label: 'Cheese', count: 3 },
      ],
    });
  const seedMine = (slugs: string[]) =>
    AsyncStorage.setItem('myCategories', JSON.stringify(slugs));

  it('lands on the Mine home when categories are chosen, showing category shelves', async () => {
    await fruitCache();
    await seedMine(['fruits']);
    await render(<DealsScreen />);

    // "Per category" (the FilterBar summary) + a "See all" shelf header prove the Mine view is
    // showing — not All (which would read "Biggest discount" with no shelf headers).
    expect(await screen.findByText('Per category')).toBeTruthy();
    expect(screen.getByLabelText('See all 2 in Fruits')).toBeTruthy();
    expect(screen.getByText('Mine')).toBeTruthy();
  });

  it('lands on All when no categories are chosen — and shows no Mine chip', async () => {
    await fruitCache(); // offers + cats present, but myCategories is unset
    await render(<DealsScreen />);

    expect(await screen.findByText('Biggest discount')).toBeTruthy(); // the All default sort
    expect(screen.queryByText('Mine')).toBeNull();
    expect(screen.queryByText('Per category')).toBeNull();
  });

  it('"See all" drills into the category’s full view, and the Mine chip returns', async () => {
    await fruitCache();
    await seedMine(['fruits']);
    await render(<DealsScreen />);
    await screen.findByText('Per category');

    await fireEvent.press(screen.getByLabelText('See all 2 in Fruits'));
    // The single-category view sorts by the Fruits default (€/kg), and the per-category summary is gone.
    expect(await screen.findByText('Cheapest €/kg')).toBeTruthy();
    expect(screen.queryByText('Per category')).toBeNull();

    await fireEvent.press(screen.getByText('Mine'));
    expect(await screen.findByText('Per category')).toBeTruthy();
  });

  it('the pencil editor toggles a category and persists it', async () => {
    await fruitCache();
    await seedMine(['fruits']);
    await render(<DealsScreen />);
    await screen.findByText('Per category');

    await fireEvent.press(screen.getByLabelText('Edit my categories'));
    const modal = await screen.findByTestId('categories-modal');
    // Fruits is already chosen ("Remove Fruits"); Cheese isn't ("Add Cheese") — add it.
    await fireEvent.press(within(modal).getByLabelText('Add Cheese'));

    await waitFor(() => {
      const writes = (AsyncStorage.setItem as jest.Mock).mock.calls.filter(
        ([k]) => k === 'myCategories',
      );
      expect(JSON.parse(writes[writes.length - 1][1])).toEqual(['fruits', 'cheese']);
    });
  });
});

/** All rendered text inside a node, flattened. RNTL's text queries only match a Text whose children
 * are a single string, so a composed <Text> (label + qty) is invisible to them. */
function flatText(node: unknown): string {
  const walk = (c: unknown): string => {
    if (c == null || c === false) return '';
    if (typeof c === 'string' || typeof c === 'number') return String(c);
    if (Array.isArray(c)) return c.map(walk).join('');
    return walk((c as { props?: { children?: unknown } }).props?.children);
  };
  return walk((node as { props?: { children?: unknown } }).props?.children);
}

describe('DealsScreen — opening a deal from the Basket picker', () => {
  // "Milch" matches the catalog's milk item, so the basket row has deals to pick from.
  const MILK = makeOffer({
    name: 'Frische Vollmilch',
    category: 'dairy',
    category_label: 'Milk & Dairy',
    price_cents: 119,
  });

  async function seedBasketWithMilk() {
    await seedCache({ offers: [MILK], cats: [] });
    await AsyncStorage.setItem(
      'basket',
      JSON.stringify([{ key: 'milk', label: 'Milk', keywords: ['milch'] }]),
    );
  }

  /** Open Basket → the item's per-item deals picker. */
  const openPicker = async () => {
    await screen.findByText('Filters');
    await fireEvent.press(screen.getByLabelText('Basket'));
    const basket = await screen.findByTestId('basket-modal');
    await fireEvent.press(await within(basket).findByText('Milk'));
    return basket;
  };

  it('separates the two actions: the card PICKS, a chevron opens the flyer', async () => {
    // Tap was already taken by "use this offer in my plan", so viewing the deal needs its own
    // control — and the card must stop claiming it opens the deal.
    await seedBasketWithMilk();
    await render(<DealsScreen />);
    const basket = await openPicker();

    expect(await within(basket).findByLabelText('Use Frische Vollmilch in your plan')).toBeTruthy();
    expect(within(basket).getByLabelText('Open deal for Frische Vollmilch')).toBeTruthy();
  });

  it('renders the deal detail INSIDE the Basket sheet, never as a sibling of it', async () => {
    // The PR #81 nesting rule: a sibling modal is refused by iOS and the refusal latches for the
    // whole session. Assert containment — moving the element up a level silently reintroduces it.
    await seedBasketWithMilk();
    await render(<DealsScreen />);
    const basket = await openPicker();

    await fireEvent.press(within(basket).getByLabelText('Open deal for Frische Vollmilch'));

    const stillBasket = await screen.findByTestId('basket-modal');
    await waitFor(() => expect(within(stillBasket).getByText('View payload')).toBeTruthy());
  });

  it('tapping the chevron does NOT pick the offer — the picker stays open', async () => {
    // The two targets must not bleed into each other: viewing a flyer shouldn't silently commit
    // that offer to the plan (picking closes the picker, so a leak is observable).
    await seedBasketWithMilk();
    await render(<DealsScreen />);
    const basket = await openPicker();

    await fireEvent.press(within(basket).getByLabelText('Open deal for Frische Vollmilch'));
    await screen.findByText('View payload');

    // Still in the picker (its card is present), i.e. pickOffer never ran.
    expect(within(basket).getByLabelText('Use Frische Vollmilch in your plan')).toBeTruthy();
  });

  it('drops the detail when the Basket closes, so it cannot change host mid-flight', async () => {
    await seedBasketWithMilk();
    await render(<DealsScreen />);
    const basket = await openPicker();
    await fireEvent.press(within(basket).getByLabelText('Open deal for Frische Vollmilch'));
    await screen.findByText('View payload');

    await fireEvent.press(within(basket).getByLabelText('Close basket'));
    await waitFor(() => expect(screen.queryByText('View payload')).toBeNull());
  });
});

describe('DealsScreen — opening a deal from a Recipes ingredient', () => {
  // "Gouda" is an ingredient in the bundled recipes, so a seeded Gouda offer resolves to an
  // on-sale row (recipes.ts only attaches an `offer` when role === 'on_sale').
  const GOUDA = makeOffer({
    name: 'Gouda jung',
    category: 'cheese',
    category_label: 'Cheese',
    price_cents: 149,
  });

  const openRecipes = async () => {
    await screen.findByText('Filters');
    await fireEvent.press(screen.getByLabelText('Recipes'));
    return screen.findByTestId('recipes-modal');
  };

  it('opens the deal detail INSIDE the Recipes sheet, never as a sibling of it', async () => {
    // The PR #81 trap once more: RN presents a Modal from the first view controller up the
    // responder chain, so a sibling detail is refused by iOS and the refusal latches for the whole
    // session. Assert containment, not mere presence — moving the element up one level in
    // DealsScreen silently reintroduces the bug.
    await seedCache({ offers: [GOUDA], cats: [{ category: 'cheese', label: 'Cheese', count: 1 }] });
    await render(<DealsScreen />);
    const recipes = await openRecipes();

    await fireEvent.press(await within(recipes).findByLabelText('Open deal for Gouda jung'));

    const stillRecipes = await screen.findByTestId('recipes-modal');
    await waitFor(() => expect(within(stillRecipes).getByText('View payload')).toBeTruthy());
  });

  it('makes the WHOLE ingredient row the tap target, not just the price', async () => {
    // The Likes row had this exact defect: only the ~45pt price block was pressable, so tapping
    // the product name did nothing (fixed in #81). The row's pressable must wrap the label too.
    await seedCache({ offers: [GOUDA], cats: [] });
    await render(<DealsScreen />);
    const recipes = await openRecipes();

    const row = await within(recipes).findByLabelText('Open deal for Gouda jung');
    // The ingredient label is a COMPOSED <Text> (name + an optional qty child), which RNTL's text
    // matcher skips, so flatten the row's own rendered text instead (cf. the RNTL notes in
    // CLAUDE.md: assert on children, not a string match, for composed Text).
    expect(flatText(row)).toContain('Gouda'); // the label is INSIDE the pressable
    expect(flatText(row)).toContain('1,49 €'); // ...and so is the price
  });

  it('leaves "have" / "buy" ingredients inert — they have no deal to open', async () => {
    await seedCache({ offers: [GOUDA], cats: [] });
    await render(<DealsScreen />);
    const recipes = await openRecipes();
    await within(recipes).findByLabelText('Open deal for Gouda jung');

    // Every openable row must be the one matched offer; staples/buy rows expose no control.
    const openable = within(recipes)
      .queryAllByLabelText(/^Open deal for /)
      .map((n) => n.props.accessibilityLabel);
    expect([...new Set(openable)]).toEqual(['Open deal for Gouda jung']);
  });

  it('drops the detail when Recipes closes, so it cannot change host mid-flight', async () => {
    await seedCache({ offers: [GOUDA], cats: [] });
    await render(<DealsScreen />);
    const recipes = await openRecipes();
    await fireEvent.press(await within(recipes).findByLabelText('Open deal for Gouda jung'));
    await screen.findByText('View payload');

    // Labelled, because the nested detail carries its own "Close" too.
    await fireEvent.press(within(recipes).getByLabelText('Close recipes'));
    await waitFor(() => expect(screen.queryByText('View payload')).toBeNull());
  });
});

describe('DealsScreen — the "My Categories" browser', () => {
  // A cache with a discounted fruit, an undiscounted one, and a cheese — enough to exercise the
  // card's "3 most discounted, filled from the default sort" rule.
  const browserCache = () =>
    seedCache({
      offers: [
        makeOffer({
          name: 'Cantaloupe-Melone',
          category: 'fruits',
          category_label: 'Fruits',
          price_cents: 149,
          regular_price_cents: 219,
          discount_pct: 32,
        }),
        makeOffer({
          name: 'Honigmelone',
          category: 'fruits',
          category_label: 'Fruits',
          price_cents: 119,
          unit_price_cents: 119,
        }),
        makeOffer({ name: 'Gouda jung', category: 'cheese', category_label: 'Cheese', price_cents: 149 }),
      ],
      cats: [
        { category: 'fruits', label: 'Fruits', count: 2 },
        { category: 'cheese', label: 'Cheese', count: 1 },
      ],
    });

  const openBrowser = async () => {
    await screen.findByText('Filters');
    await fireEvent.press(screen.getByLabelText('My Categories'));
    return screen.findByTestId('categories-browser');
  };

  it('replaces the Compare header icon (a 7th action overflows 375pt)', async () => {
    await browserCache();
    await render(<DealsScreen />);
    await screen.findByText('Filters');

    expect(screen.getByLabelText('My Categories')).toBeTruthy();
    // Compare moved into the browser — it must no longer occupy a header slot.
    expect(screen.queryByLabelText('Compare stores')).toBeNull();
  });

  it('lists every category as a card with its deal count and headline deals', async () => {
    await browserCache();
    await render(<DealsScreen />);
    const browser = await openBrowser();

    expect(within(browser).getByLabelText('Open Fruits, 2 deals')).toBeTruthy();
    expect(within(browser).getByLabelText('Open Cheese, 1 deal')).toBeTruthy();
    // The discounted fruit leads; the undiscounted one still fills a row (the Butter case).
    expect(within(browser).getByText('Cantaloupe-Melone')).toBeTruthy();
    expect(within(browser).getByText('Honigmelone')).toBeTruthy();
  });

  it('tapping a card opens that category in the deals list', async () => {
    await browserCache();
    await render(<DealsScreen />);
    const browser = await openBrowser();

    await fireEvent.press(within(browser).getByLabelText('Open Fruits, 2 deals'));

    // The browser closes and the list is now the single-category view (its €/kg default sort).
    await waitFor(() => expect(screen.queryByTestId('categories-browser')).toBeNull());
    expect(await screen.findByText('Cheapest €/kg')).toBeTruthy();
  });

  it('renders the Mine editor INSIDE the browser, never as a sibling of it', async () => {
    // The PR #81 constraint, one level deeper: RN presents a Modal from the first view controller
    // up the responder chain, so a sibling editor would be refused by iOS — and that refusal
    // latches for the whole session. Moving the element up a level silently reintroduces it, so
    // assert containment rather than mere presence.
    await browserCache();
    await render(<DealsScreen />);
    const browser = await openBrowser();

    await fireEvent.press(within(browser).getByLabelText('Edit my categories'));

    const stillBrowser = await screen.findByTestId('categories-browser');
    await waitFor(() =>
      expect(within(stillBrowser).getByTestId('categories-modal')).toBeTruthy(),
    );
  });

  it('leaving the browser drops its nested editor, so it cannot resurface over what opens next', async () => {
    // Measured on web: with the editor open, tapping a card (or Compare) closed the browser but
    // left `categoriesModal` true — so the editor re-mounted at the ROOT branch and sat on top of
    // the next screen. Same class as the Likes closers dropping the deal detail.
    await browserCache();
    await render(<DealsScreen />);
    const browser = await openBrowser();
    await fireEvent.press(within(browser).getByLabelText('Edit my categories'));
    await screen.findByTestId('categories-modal');

    await fireEvent.press(within(browser).getByLabelText('Open Fruits, 2 deals'));

    await waitFor(() => expect(screen.queryByTestId('categories-browser')).toBeNull());
    expect(screen.queryByTestId('categories-modal')).toBeNull(); // must not survive at root
  });

  it('gives the browser and the editor distinct close labels', async () => {
    // Both announced "Close my categories" — ambiguous for a screen reader when one is inside
    // the other, and it made the two indistinguishable to any label-based query.
    await browserCache();
    await render(<DealsScreen />);
    const browser = await openBrowser();
    await fireEvent.press(within(browser).getByLabelText('Edit my categories'));
    await screen.findByTestId('categories-modal');

    expect(screen.getByLabelText('Close my categories')).toBeTruthy(); // the browser
    expect(screen.getByLabelText('Close category picker')).toBeTruthy(); // the editor
  });

  it('the Mine/All toggle switches which categories are listed', async () => {
    await browserCache();
    await AsyncStorage.setItem('myCategories', JSON.stringify(['cheese']));
    await render(<DealsScreen />);
    const browser = await openBrowser();

    // Opens on Mine (categories are chosen), so only Cheese has a card.
    expect(within(browser).getByLabelText('Open Cheese, 1 deal')).toBeTruthy();
    expect(within(browser).queryByLabelText('Open Fruits, 2 deals')).toBeNull();

    await fireEvent.press(within(browser).getByText('All'));
    expect(await within(browser).findByLabelText('Open Fruits, 2 deals')).toBeTruthy();
  });
});

describe('DealsScreen — per-category sort', () => {
  // One global sort couldn't fit both: €/kg is the axis you shop Fruits on (and out-covers
  // "Biggest discount" there, 77% vs 47% measured), while household is only 25% €/kg-covered.
  // Asserts the RENDERED label, not the state — the sort must visibly say what it's doing.
  async function seedFruitCache() {
    await seedCache({
      offers: [
        makeOffer({ name: 'Bananen', category: 'fruits', category_label: 'Fruits' }),
        makeOffer({ name: 'Äpfel', category: 'fruits', category_label: 'Fruits' }),
      ],
      cats: [{ category: 'fruits', label: 'Fruits', count: 2 }],
    });
  }

  it('switches to €/kg when a food category is selected, and back to discount in All', async () => {
    await seedFruitCache();
    await render(<DealsScreen />);

    // "All" keeps the deal-hunting default — the app's headline.
    await waitFor(() => expect(screen.getByText('Biggest discount')).toBeTruthy());

    fireEvent.press(screen.getByText('Fruits (2)'));
    await waitFor(() => expect(screen.getByText('Cheapest €/kg')).toBeTruthy());

    fireEvent.press(screen.getByText('All'));
    await waitFor(() => expect(screen.getByText('Biggest discount')).toBeTruthy());
  });

  it('honours a stored per-category override instead of the default', async () => {
    await seedFruitCache();
    await AsyncStorage.setItem('sortByCategory', JSON.stringify({ fruits: 'price' }));

    await render(<DealsScreen />);
    fireEvent.press(screen.getByText('Fruits (2)'));

    // The user's pick for Fruits wins over the €/kg default.
    await waitFor(() => expect(screen.getByText('Lowest price')).toBeTruthy());
  });
});

describe('DealsScreen — Hide / Un-Hide a deal', () => {
  // NOTE: every fireEvent is awaited. RNTL v14's fireEvent.press returns a Promise (like
  // render); leaving one dangling opens overlapping act() scopes and the state update is
  // silently DROPPED — the press appears to fire and nothing happens.
  async function seedHidden() {
    // A hide is stored by identity, so a test can seed one exactly as the app writes it.
    await AsyncStorage.setItem(
      'hiddenItems',
      JSON.stringify([
        { key: 'lidl:cached bergkäse', name: 'Cached Bergkäse', chain: 'lidl', hiddenAt: NOW },
      ]),
    );
  }

  const openDetail = async () => {
    await screen.findByText('Cached Bergkäse');
    await fireEvent.press(screen.getAllByLabelText('Open deal for Cached Bergkäse')[0]);
    await screen.findByText('View payload');
  };

  const revealHidden = async () => {
    await fireEvent.press(screen.getByText('Filters'));
    await fireEvent.press(await screen.findByText('Show hidden (1)'));
    await fireEvent.press(screen.getByText('Done'));
  };

  it('Hide closes the detail and drops the deal from the list, in one press', async () => {
    await seedCache();
    await render(<DealsScreen />);
    await openDetail();

    await fireEvent.press(screen.getByLabelText('Hide Cached Bergkäse'));

    // Hiding is a dismissal: no second tap on Close should be needed.
    await waitFor(() => expect(screen.queryByText('View payload')).toBeNull());
    // ...and the deal is gone from the list behind it.
    expect(screen.queryByText('Cached Bergkäse')).toBeNull();
  });

  it('persists the hide keyed on chain+name, never the churning offer id', async () => {
    await seedCache();
    await render(<DealsScreen />);
    await openDetail();
    await fireEvent.press(screen.getByLabelText('Hide Cached Bergkäse'));

    await waitFor(() => {
      const writes = (AsyncStorage.setItem as jest.Mock).mock.calls.filter(
        ([k]) => k === 'hiddenItems',
      );
      expect(writes.length).toBeGreaterThan(0);
      const stored = JSON.parse(writes[writes.length - 1][1]);
      // /api/reset deletes every row and Render's DB is ephemeral, so SQLite reuses rowids:
      // an id-keyed hide would follow a different product next week.
      expect(stored[0].key).toBe('lidl:cached bergkäse');
    });
  });

  it('keeps a hidden deal out of the list', async () => {
    await seedCache();
    await seedHidden();
    await render(<DealsScreen />);
    await screen.findByText('Filters'); // the screen is up...
    expect(screen.queryByText('Cached Bergkäse')).toBeNull(); // ...but the deal is gone
  });

  it('Filters → "Show hidden" is the route back: it reveals the deal so it can be un-hidden', async () => {
    await seedCache();
    await seedHidden();
    await render(<DealsScreen />);
    await screen.findByText('Filters');
    await revealHidden();

    await openDetail();
    expect(screen.getByLabelText('Un-hide Cached Bergkäse')).toBeTruthy();

    // Un-hide → it belongs in the normal list again.
    await fireEvent.press(screen.getByLabelText('Un-hide Cached Bergkäse'));
    expect(await screen.findByLabelText('Hide Cached Bergkäse')).toBeTruthy();
  });

  it('offers no Hidden section until something is actually hidden', async () => {
    await seedCache();
    await render(<DealsScreen />);
    await screen.findByText('Cached Bergkäse');
    await fireEvent.press(screen.getByText('Filters'));
    await screen.findByText('Sort by');
    expect(screen.queryByText(/Show hidden/)).toBeNull();
  });

  it('Reset clears the lens but NOT the hidden set — hiding is a persisted choice', async () => {
    await seedCache();
    await seedHidden();
    await render(<DealsScreen />);
    await screen.findByText('Filters');
    await revealHidden();
    expect(await screen.findByText('Cached Bergkäse')).toBeTruthy(); // lens on

    await fireEvent.press(screen.getByText('Filters'));
    await fireEvent.press(screen.getByText('Reset'));

    // Lens off → hidden again; the hide itself survived (only "Reset all app data" clears it).
    await waitFor(() => expect(screen.queryByText('Cached Bergkäse')).toBeNull());
    expect(screen.getByText('Show hidden (1)')).toBeTruthy();
  });
});
