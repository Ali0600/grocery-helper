// Pins the swipe→action seam (`handleSwipeableOpen`). The legacy Swipeable's `direction`
// is the PANEL SIDE that opened (not the finger motion): 'right' panel = left-swipe =
// basket, 'left' panel = right-swipe = Like. The pre-Like code early-returned on
// anything but 'right', so the regression this guards is "Like becomes a silent no-op".
// The native pan itself can't run under jest — the exported handler is the seam.
import { handleSwipeableOpen } from '../components/SwipeableOfferCard';
import { makeOffer } from './fixtures';

const flushFrame = () => new Promise((r) => setTimeout(r, 0));

function open(direction: 'left' | 'right') {
  const offer = makeOffer({ name: 'McCain Golden Longs' });
  const onAdd = jest.fn();
  const onLike = jest.fn();
  const close = jest.fn();
  handleSwipeableOpen(direction, { close }, offer, { onAdd, onLike });
  return { offer, onAdd, onLike, close };
}

describe('handleSwipeableOpen', () => {
  it('right-swipe (left panel) likes the offer', async () => {
    const { offer, onAdd, onLike, close } = open('left');
    // Close fires synchronously, BEFORE the deferred action (freeze hardening).
    expect(close).toHaveBeenCalled();
    expect(onLike).not.toHaveBeenCalled(); // …the action itself is deferred a frame
    await flushFrame();
    expect(onLike).toHaveBeenCalledWith(offer);
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('left-swipe (right panel) still adds to the basket', async () => {
    const { offer, onAdd, onLike, close } = open('right');
    expect(close).toHaveBeenCalled();
    await flushFrame();
    expect(onAdd).toHaveBeenCalledWith(offer);
    expect(onLike).not.toHaveBeenCalled();
  });
});
