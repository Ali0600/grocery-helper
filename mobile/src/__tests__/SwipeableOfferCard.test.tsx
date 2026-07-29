// Pins the swipe→action seam (`handleSwipeableOpen`). The legacy Swipeable's `direction` is
// the PANEL SIDE that opened, NOT the finger motion: 'right' panel = left-swipe = basket,
// 'left' panel = right-swipe = hide. Getting that backwards silently swaps the two gestures,
// and the native pan can't run under jest — the exported handler is the only seam that can
// catch it. (Right-swipe used to Like; it hides now.)
import { handleSwipeableOpen } from '../components/SwipeableOfferCard';
import { makeOffer } from './fixtures';

const flushFrame = () => new Promise((r) => setTimeout(r, 0));

function open(direction: 'left' | 'right') {
  const offer = makeOffer({ name: 'McCain Golden Longs' });
  const onAdd = jest.fn();
  const onHide = jest.fn();
  const close = jest.fn();
  handleSwipeableOpen(direction, { close }, offer, { onAdd, onHide });
  return { offer, onAdd, onHide, close };
}

describe('handleSwipeableOpen', () => {
  it('right-swipe (left panel) hides the offer', async () => {
    const { offer, onAdd, onHide, close } = open('left');
    // Close fires synchronously, BEFORE the deferred action (freeze hardening).
    expect(close).toHaveBeenCalled();
    expect(onHide).not.toHaveBeenCalled(); // …the action itself is deferred a frame
    await flushFrame();
    expect(onHide).toHaveBeenCalledWith(offer);
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('left-swipe (right panel) still adds to the basket', async () => {
    const { offer, onAdd, onHide, close } = open('right');
    expect(close).toHaveBeenCalled();
    await flushFrame();
    expect(onAdd).toHaveBeenCalledWith(offer);
    expect(onHide).not.toHaveBeenCalled();
  });
});
