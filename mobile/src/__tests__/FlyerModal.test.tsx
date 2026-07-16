// The deal detail's Like/Basket buttons — the NON-GESTURE path to the two swipe actions.
// A swipe is unreachable for screen-reader/keyboard users, and Like had no other entry
// point at all, so these buttons are the accessibility fix: they must fire, and they must
// not look actionable once the product is already added.
import { fireEvent, render, screen } from '@testing-library/react-native';
import React from 'react';

import { FlyerModal } from '../components/FlyerModal';
import { makeOffer } from './fixtures';

jest.mock('../api', () => ({ api: { offerPayload: jest.fn() } }));
jest.mock('../storage', () => ({ getPayloadCache: jest.fn().mockResolvedValue(null) }));

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
