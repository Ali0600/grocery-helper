// The deal detail's Like/Basket buttons — the NON-GESTURE path to the two swipe actions.
// A swipe is unreachable for screen-reader/keyboard users, and Like had no other entry
// point at all, so these buttons are the accessibility fix: they must fire, and they must
// not look actionable once the product is already added.
import { fireEvent, render, screen } from '@testing-library/react-native';
import React from 'react';

import { api } from '../api';
import { FlyerModal } from '../components/FlyerModal';
import { getTraceCache } from '../storage';
import { makeOffer } from './fixtures';

// Both module mocks are PARTIAL — every module FlyerModal imports from them must appear
// here, or the missing export lands as `undefined` and the component throws at call time.
jest.mock('../api', () => ({
  api: { offerPayload: jest.fn(), offerCategoryTrace: jest.fn() },
}));
jest.mock('../storage', () => ({
  getPayloadCache: jest.fn().mockResolvedValue(null),
  getTraceCache: jest.fn().mockResolvedValue(null),
}));

const offer = makeOffer({ name: 'McCain Golden Longs', chain: 'lidl', price_cents: 299 });
const noop = () => {};

describe('FlyerModal — Like / Basket buttons', () => {
  it('Like fires onLike with the offer', async () => {
    const onLike = jest.fn();
    await render(<FlyerModal offer={offer} onClose={noop} onLike={onLike} onAddToBasket={noop} />);
    fireEvent.press(screen.getByLabelText('Like McCain Golden Longs'));
    expect(onLike).toHaveBeenCalledWith(offer);
  });

  it('Basket fires onAddToBasket with the offer', async () => {
    const onAdd = jest.fn();
    await render(<FlyerModal offer={offer} onClose={noop} onLike={noop} onAddToBasket={onAdd} />);
    fireEvent.press(screen.getByLabelText('Add McCain Golden Longs to basket'));
    expect(onAdd).toHaveBeenCalledWith(offer);
  });

  it('shows a done state and does NOT fire once already liked', async () => {
    const onLike = jest.fn();
    await render(
      <FlyerModal offer={offer} onClose={noop} onLike={onLike} onAddToBasket={noop} liked />,
    );
    expect(screen.getByText('Liked ✓')).toBeTruthy();
    // Disabled, so an already-liked product can't be re-added from here (the swipe path's
    // "already in your likes" toast would be invisible behind this modal anyway).
    fireEvent.press(screen.getByLabelText('McCain Golden Longs is in your likes'));
    expect(onLike).not.toHaveBeenCalled();
  });

  it('shows a done state and does NOT fire once already in the basket', async () => {
    const onAdd = jest.fn();
    await render(
      <FlyerModal offer={offer} onClose={noop} onLike={noop} onAddToBasket={onAdd} inBasket />,
    );
    expect(screen.getByText('In basket ✓')).toBeTruthy();
    fireEvent.press(screen.getByLabelText('McCain Golden Longs is in your basket'));
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('renders nothing actionable with no offer', async () => {
    await render(<FlyerModal offer={null} onClose={noop} onLike={noop} onAddToBasket={noop} />);
    expect(screen.queryByText('Like')).toBeNull();
  });
});


// --- "Why this category?" — the classifier trace ------------------------------------

const trace = (over: Record<string, unknown> = {}) => ({
  id: offer.id,
  stored_category: 'pork',
  stored_label: 'Pork & Sausage',
  computed_category: 'pork',
  computed_label: 'Pork & Sausage',
  stale: false,
  trace: {
    category: 'pork',
    inputs: { category_path: ['Lebensmittel und Getränke', 'Fisch', 'Lachs'] },
    layers: [
      { layer: '0', status: 'no_match' },
      { layer: '1', status: 'skipped', reason: 'path_is_food_root' },
      {
        layer: '2', status: 'decided', slug: 'pork', table: '_FORM_OVERRIDES',
        index: 10, matched: 'lachsschinken', where: 'name_text',
      },
      { layer: '2b', status: 'skipped', reason: 'no_unit' },
      { layer: '3', status: 'decided', slug: 'fish', table: '_PATH_MAP', matched: 'Lachs' },
      { layer: '4', status: 'no_match' },
      { layer: '5', status: 'no_match' },
      { layer: '6', status: 'no_match' },
      { layer: '7', status: 'decided', slug: 'other', reason: 'fallback' },
    ],
  },
  ...over,
});

describe('FlyerModal — Why this category?', () => {
  beforeEach(() => jest.clearAllMocks());

  it('reads the prefetched cache instead of the network, and names the deciding rule', async () => {
    (getTraceCache as jest.Mock).mockResolvedValue({ byId: { [String(offer.id)]: trace() } });
    await render(<FlyerModal offer={offer} onClose={noop} />);
    await fireEvent.press(screen.getByLabelText('Why this category?'));

    // The verdict names the layer AND the token, so the report is actionable as-is.
    expect(await screen.findByText(/Form words "lachsschinken"/)).toBeTruthy();
    // The editable address of the rule.
    expect(screen.getByText(/_FORM_OVERRIDES\[10\]/)).toBeTruthy();
    // The cache hit must not have cost a network call (the point of the prefetch).
    expect(api.offerCategoryTrace).not.toHaveBeenCalled();
  });

  it('shows what the LOSING layers would have said', async () => {
    (getTraceCache as jest.Mock).mockResolvedValue({ byId: { [String(offer.id)]: trace() } });
    await render(<FlyerModal offer={offer} onClose={noop} />);
    await fireEvent.press(screen.getByLabelText('Why this category?'));
    // Layer 3's path says fish — that's how you tell a wrong rule from one holding the line.
    expect(await screen.findByText(/Path node → fish/)).toBeTruthy();
  });

  it('surfaces the source path, which the deals API does not expose', async () => {
    (getTraceCache as jest.Mock).mockResolvedValue({ byId: { [String(offer.id)]: trace() } });
    await render(<FlyerModal offer={offer} onClose={noop} />);
    await fireEvent.press(screen.getByLabelText('Why this category?'));
    expect(await screen.findByText(/Lebensmittel und Getränke › Fisch › Lachs/)).toBeTruthy();
  });

  it('warns when the stored category predates a rules change', async () => {
    (getTraceCache as jest.Mock).mockResolvedValue({
      byId: {
        [String(offer.id)]: trace({
          stored_category: 'beef', stored_label: 'Beef', stale: true,
        }),
      },
    });
    await render(<FlyerModal offer={offer} onClose={noop} />);
    await fireEvent.press(screen.getByLabelText('Why this category?'));
    expect(await screen.findByText(/Shown as Beef, but the current rules say/)).toBeTruthy();
  });

  it('falls back to the network when the offer was not prefetched', async () => {
    (getTraceCache as jest.Mock).mockResolvedValue({ byId: {} });
    (api.offerCategoryTrace as jest.Mock).mockResolvedValue(trace());
    await render(<FlyerModal offer={offer} onClose={noop} />);
    await fireEvent.press(screen.getByLabelText('Why this category?'));
    expect(await screen.findByText(/Form words "lachsschinken"/)).toBeTruthy();
    expect(api.offerCategoryTrace).toHaveBeenCalledWith(offer.id);
  });
});
