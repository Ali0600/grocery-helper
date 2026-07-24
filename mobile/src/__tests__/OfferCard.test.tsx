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
    expect(screen.queryByLabelText('Liked')).toBeNull();
  });

  it('shows a heart marker when the offer is liked', async () => {
    await render(<OfferCard offer={offer} onPress={() => {}} liked />);
    expect(screen.getByLabelText('Liked')).toBeTruthy();
    expect(screen.queryByLabelText('In your basket')).toBeNull();
  });

  it('shows neither marker by default', async () => {
    await render(<OfferCard offer={offer} onPress={() => {}} />);
    expect(screen.queryByLabelText('Liked')).toBeNull();
    expect(screen.queryByLabelText('In your basket')).toBeNull();
  });

  it('can show both at once', async () => {
    await render(<OfferCard offer={offer} onPress={() => {}} liked inBasket />);
    expect(screen.getByLabelText('Liked')).toBeTruthy();
    expect(screen.getByLabelText('In your basket')).toBeTruthy();
  });

  it('folds the status into the card’s spoken label (the markers aren’t separately focusable)', async () => {
    // A screen reader only hears the row button's label, so the status has to live there too.
    await render(<OfferCard offer={offer} onPress={() => {}} liked inBasket />);
    expect(screen.getByLabelText('Open deal for McCain Golden Longs, in your basket, liked')).toBeTruthy();
  });

  it('leaves the spoken label plain when neither is set', async () => {
    await render(<OfferCard offer={offer} onPress={() => {}} />);
    expect(screen.getByLabelText('Open deal for McCain Golden Longs')).toBeTruthy();
  });
});
