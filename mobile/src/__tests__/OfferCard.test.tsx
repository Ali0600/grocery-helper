// OfferCard's status markers: a heart when the product is already liked, a cart when it's already
// in the basket — so you can tell from the list without opening the flyer. Icon-only in the tag
// row; the status is also folded into the card's spoken label. RNTL v14: `await render`.
import { render, screen } from '@testing-library/react-native';
import React from 'react';

import { OfferCard } from '../components/OfferCard';
import { makeOffer } from './fixtures';

const offer = makeOffer({ name: 'McCain Golden Longs' });

describe('OfferCard status markers', () => {
  it('shows a cart marker when the offer is in the basket', async () => {
    await render(<OfferCard offer={offer} onPress={() => {}} inBasket />);
    expect(screen.getByLabelText('In your basket')).toBeTruthy();
  });

  it('shows no marker by default', async () => {
    await render(<OfferCard offer={offer} onPress={() => {}} />);
    expect(screen.queryByLabelText('In your basket')).toBeNull();
  });

  it('has no Liked marker any more — liking is gone', async () => {
    // History replaced Likes and is auto-populated from basket adds, so a per-card badge
    // would end up on most rows. The cart marker (what's in the basket NOW) is the one left.
    await render(<OfferCard offer={offer} onPress={() => {}} inBasket />);
    expect(screen.queryByLabelText('Liked')).toBeNull();
  });

  it('folds the basket status into the card’s spoken label (the marker isn’t separately focusable)', async () => {
    // A screen reader only hears the row button's label, so the status has to live there too.
    await render(<OfferCard offer={offer} onPress={() => {}} inBasket />);
    expect(
      screen.getByLabelText('Open deal for McCain Golden Longs, in your basket'),
    ).toBeTruthy();
  });

  it('leaves the spoken label plain when it is not in the basket', async () => {
    await render(<OfferCard offer={offer} onPress={() => {}} />);
    expect(screen.getByLabelText('Open deal for McCain Golden Longs')).toBeTruthy();
  });
});
