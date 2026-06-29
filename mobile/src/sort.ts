import { SortMode } from './storage';

// The three sort modes + their labels, shared by the filter sheet (the selector)
// and the filter bar (the "Sort: …" summary). Order = display order.
export const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: 'price', label: 'Lowest price' },
  { value: 'discount', label: 'Biggest discount' },
  { value: 'unit', label: 'Cheapest €/kg' },
];

export const sortLabel = (mode: SortMode): string =>
  SORT_OPTIONS.find((o) => o.value === mode)?.label ?? '';
