/** Cents -> German-style euro string, e.g. 139 -> "1,39 €". */
export const euro = (cents: number): string =>
  (cents / 100).toFixed(2).replace('.', ',') + ' €';

/** Discount percent -> badge label, e.g. 41.8 -> "-42%". */
export const pct = (p: number | null): string =>
  p == null ? '' : `-${Math.round(p)}%`;

/**
 * Tidy a Lidl unit string for display:
 *   "Je 150 g (Max. 24 Stück)" -> "150 g"
 * Drops purchase-limit parentheticals and the leading "Je ". Price-per-unit
 * fallbacks like "1 kg = 1.93" have neither, so they pass through unchanged.
 */
export const cleanUnit = (unit: string | null): string | null => {
  if (!unit) return null;
  const u = unit
    .replace(/\s*\([^)]*\)/g, '') // drop "(Max. 24 Stück)" etc.
    .replace(/^je\s+/i, '') // drop leading "Je "
    .trim();
  return u || null;
};

/**
 * Title-case shouting brands for display: "EHRMANN" -> "Ehrmann",
 * "RITTER SPORT" -> "Ritter Sport". Brands that already carry lower-case
 * (intentionally styled, e.g. "LIVARNO home") are left untouched.
 */
export const formatBrand = (brand: string | null): string | null => {
  if (!brand) return null;
  if (brand !== brand.toUpperCase()) return brand; // already styled
  return brand.toLowerCase().replace(/\b\p{L}/gu, (c) => c.toUpperCase());
};
