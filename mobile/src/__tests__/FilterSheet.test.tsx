// The Filters sheet's "Only show" row — the one MULTI-select control in the sheet.
//
// It used to be single-select, so the interesting cases are the ones the old behaviour would
// get wrong: pressing an already-selected store must remove just that one (not clear the whole
// lens), and several stores must be able to read as selected at the same time.

import { fireEvent, render, screen } from '@testing-library/react-native';
import React from 'react';

import { FilterSheet } from '../components/FilterSheet';

const noop = () => {};

const props = (over: Partial<React.ComponentProps<typeof FilterSheet>> = {}) => ({
  visible: true,
  onClose: noop,
  onReset: noop,
  sortMode: 'discount' as const,
  onChangeSort: noop,
  chains: ['lidl', 'rewe', 'edeka'],
  chainCounts: { lidl: 120, rewe: 80, edeka: 60 },
  storeLens: [] as string[],
  onToggleStoreLens: noop as (c: string) => void,
  onClearStoreLens: noop,
  hasDayLimited: false,
  dayLimitedCount: 0,
  specialDays: false,
  onChangeSpecialDays: noop,
  hasBio: false,
  bioCount: 0,
  bioOnly: false,
  onChangeBio: noop,
  showNonFood: false,
  nonFoodCount: 0,
  onToggleNonFood: noop,
  hiddenCount: 0,
  showHidden: false,
  onChangeShowHidden: noop,
  ...over,
});

describe('FilterSheet — "Only show" stores', () => {
  it('offers every visible chain plus All', async () => {
    await render(<FilterSheet {...props()} />);
    expect(screen.getByLabelText('All stores')).toBeTruthy();
    expect(screen.getByLabelText('Only Lidl')).toBeTruthy();
    expect(screen.getByLabelText('Only REWE')).toBeTruthy();
    expect(screen.getByLabelText('Only Edeka')).toBeTruthy();
  });

  it('is hidden when there is only one store to choose between', async () => {
    await render(<FilterSheet {...props({ chains: ['lidl'] })} />);
    expect(screen.queryByLabelText('All stores')).toBeNull();
    expect(screen.queryByLabelText('Only Lidl')).toBeNull();
  });

  it('reports SEVERAL stores as selected at once', async () => {
    await render(<FilterSheet {...props({ storeLens: ['lidl', 'edeka'] })} />);
    expect(screen.getByLabelText('Only Lidl').props.accessibilityState.selected).toBe(true);
    expect(screen.getByLabelText('Only Edeka').props.accessibilityState.selected).toBe(true);
    expect(screen.getByLabelText('Only REWE').props.accessibilityState.selected).toBe(false);
    expect(screen.getByLabelText('All stores').props.accessibilityState.selected).toBe(false);
  });

  it('marks All as selected when nothing is picked', async () => {
    await render(<FilterSheet {...props()} />);
    expect(screen.getByLabelText('All stores').props.accessibilityState.selected).toBe(true);
    expect(screen.getByLabelText('Only Lidl').props.accessibilityState.selected).toBe(false);
  });

  it('adds a store to the selection', async () => {
    const onToggleStoreLens = jest.fn();
    await render(<FilterSheet {...props({ storeLens: ['lidl'], onToggleStoreLens })} />);
    await fireEvent.press(screen.getByLabelText('Only Edeka'));
    expect(onToggleStoreLens).toHaveBeenCalledWith('edeka');
  });

  it('pressing an ALREADY-SELECTED store removes just that one, not the whole lens', async () => {
    // The single-select version cleared everything here — which is what makes multi-select
    // unusable: you could never deselect one of two picks.
    const onToggleStoreLens = jest.fn();
    const onClearStoreLens = jest.fn();
    await render(
      <FilterSheet {...props({ storeLens: ['lidl', 'edeka'], onToggleStoreLens, onClearStoreLens })} />,
    );
    await fireEvent.press(screen.getByLabelText('Only Lidl'));
    expect(onToggleStoreLens).toHaveBeenCalledWith('lidl');
    expect(onClearStoreLens).not.toHaveBeenCalled();
  });

  it('All clears the whole selection', async () => {
    const onClearStoreLens = jest.fn();
    const onToggleStoreLens = jest.fn();
    await render(
      <FilterSheet {...props({ storeLens: ['lidl', 'edeka'], onClearStoreLens, onToggleStoreLens })} />,
    );
    await fireEvent.press(screen.getByLabelText('All stores'));
    expect(onClearStoreLens).toHaveBeenCalled();
    expect(onToggleStoreLens).not.toHaveBeenCalled();
  });

  it('shows each store’s deal count', async () => {
    await render(<FilterSheet {...props()} />);
    expect(screen.getByText('Lidl (120)')).toBeTruthy();
  });
});
