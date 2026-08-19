// Pins the swipe→action seam (`handleSwipeableOpen`). The legacy Swipeable's `direction` is
// the PANEL SIDE that opened, NOT the finger motion: 'right' panel = left-swipe = basket,
// 'left' panel = right-swipe = hide. Getting that backwards silently swaps the two gestures,
// and the native pan can't run under jest — the exported handler is the only seam that can
// catch it. (Right-swipe used to Like; it hides now.)
import { render, screen } from '@testing-library/react-native';
import React from 'react';

import { handleSwipeableOpen, SwipeableOfferCard } from '../components/SwipeableOfferCard';
import { makeOffer } from './fixtures';

const flushFrame = () => new Promise((r) => setTimeout(r, 0));

function open(direction: 'left' | 'right') {
  const offer = makeOffer({ name: 'McCain Golden Longs' });
  const onBasket = jest.fn();
  const onHide = jest.fn();
  const close = jest.fn();
  handleSwipeableOpen(direction, { close }, offer, { onBasket, onHide });
  return { offer, onBasket, onHide, close };
}

describe('handleSwipeableOpen', () => {
  it('right-swipe (left panel) hides the offer', async () => {
    const { offer, onBasket, onHide, close } = open('left');
    // Close fires synchronously, BEFORE the deferred action (freeze hardening).
    expect(close).toHaveBeenCalled();
    expect(onHide).not.toHaveBeenCalled(); // …the action itself is deferred a frame
    await flushFrame();
    expect(onHide).toHaveBeenCalledWith(offer);
    expect(onBasket).not.toHaveBeenCalled();
  });

  it('left-swipe (right panel) still routes to the basket', async () => {
    const { offer, onBasket, onHide, close } = open('right');
    expect(close).toHaveBeenCalled();
    await flushFrame();
    expect(onBasket).toHaveBeenCalledWith(offer);
    expect(onHide).not.toHaveBeenCalled();
  });
});

// The left-swipe is a TOGGLE, so on an already-basketed row it REMOVES. A panel that always
// said "Basket" would be telling you the opposite of what the gesture is about to do — and
// the row is only distinguishable by the marker the same `inBasket` flag draws.
describe('the swipe panel names the action it will perform', () => {
  const renderRow = (inBasket: boolean) =>
    render(
      <SwipeableOfferCard
        offer={makeOffer({ name: 'McCain Golden Longs' })}
        onPressOffer={() => {}}
        onBasket={() => {}}
        onHide={() => {}}
        inBasket={inBasket}
      />,
    );

  it('reads "Basket" when the product is not in the basket', async () => {
    await renderRow(false);
    expect(screen.getByText('Basket')).toBeTruthy();
    expect(screen.queryByText('Remove')).toBeNull();
  });

  it('reads "Remove" once it is', async () => {
    await renderRow(true);
    expect(screen.getByText('Remove')).toBeTruthy();
    expect(screen.queryByText('Basket')).toBeNull();
  });
});
