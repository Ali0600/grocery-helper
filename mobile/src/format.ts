/** Cents -> German-style euro string, e.g. 139 -> "1,39 €". */
export const euro = (cents: number): string =>
  (cents / 100).toFixed(2).replace('.', ',') + ' €';

/** Discount percent -> badge label, e.g. 41.8 -> "-42%". */
export const pct = (p: number | null): string =>
  p == null ? '' : `-${Math.round(p)}%`;
