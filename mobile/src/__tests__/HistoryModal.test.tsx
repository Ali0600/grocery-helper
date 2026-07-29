// The Likes page's rendered contract: an on-sale like shows its current cheapest deal,
// a renamed like falls back to "More from <brand>", and ✕ removes. RNTL v14: `render`
// is async — always `await render(...)`.
import { fireEvent, render, screen } from '@testing-library/react-native';
import React from 'react';

import { HistoryModal } from '../components/HistoryModal';
import { HistoryItem } from '../types';
import { makeOffer } from './fixtures';

const liked: HistoryItem = {
  key: 'mccain golden longs',
  name: 'McCain Golden Longs',
  brand: 'McCain',
  group: null,
  groupLabel: null,
  chain: 'lidl',
  addedPriceCents: 299,
  addedAt: 1,
};

const noop = () => {};

describe('HistoryModal', () => {
  it('shows the empty state when nothing is liked', async () => {
    await render(
      <HistoryModal visible items={[]} offers={[]} onRemove={noop} onOpenOffer={noop} onClose={noop} />,
    );
    expect(screen.getByText(/Add a deal to your basket/)).toBeTruthy();
  });

  it('renders an on-sale like with its cheapest current deal, tappable to the detail', async () => {
    const offers = [
      makeOffer({ name: 'McCain Golden Longs', chain: 'edeka', price_cents: 349 }),
      makeOffer({ name: 'McCain Golden Longs', chain: 'lidl', price_cents: 279 }),
    ];
    const onOpenOffer = jest.fn();
    await render(
      <HistoryModal
        visible
        items={[liked]}
        offers={offers}
        onRemove={noop}
        onOpenOffer={onOpenOffer}
        onClose={noop}
      />,
    );
    expect(screen.getByText('2,79 €')).toBeTruthy(); // cheapest headlines
    expect(screen.getByText(/2 deals/)).toBeTruthy();
    fireEvent.press(screen.getByLabelText('Open deal for McCain Golden Longs'));
    expect(onOpenOffer).toHaveBeenCalledWith(expect.objectContaining({ price_cents: 279 }));
  });

  it('falls back to "More from <brand>" when the exact name is gone (the rename case)', async () => {
    const offers = [makeOffer({ name: 'McCain Golden Long', brand: 'McCain', price_cents: 279 })];
    await render(
      <HistoryModal
        visible
        items={[liked]}
        offers={offers}
        onRemove={noop}
        onOpenOffer={noop}
        onClose={noop}
      />,
    );
    expect(screen.getByText('Not on sale this week')).toBeTruthy();
    expect(screen.getByText('More from McCain')).toBeTruthy();
    expect(screen.getByText('McCain Golden Long')).toBeTruthy();
  });

  it('removes a like via its ✕', async () => {
    const onRemove = jest.fn();
    await render(
      <HistoryModal
        visible
        items={[liked]}
        offers={[]}
        onRemove={onRemove}
        onOpenOffer={noop}
        onClose={noop}
      />,
    );
    fireEvent.press(screen.getByLabelText('Remove McCain Golden Longs from history'));
    expect(onRemove).toHaveBeenCalledWith('mccain golden longs');
  });
});
