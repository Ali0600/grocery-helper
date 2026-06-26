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
 * Format a source per-unit price for display -> "13,32 €/kg". Handles both shapes
 * the scrapers produce: "1 kg = 13.33" (strip the leading "1 ", German comma) and
 * the bare "22.79 €/kg" / "0.46 €/Stk.". Multi-variant ranges show the first value.
 */
export const fmtPricePerUnit = (ppu: string | null): string | null => {
  if (!ppu) return null;
  if (ppu.includes('=')) {
    const [left, right] = ppu.split('=');
    const unit = left.trim().replace(/^1\s+/, ''); // "1 kg" -> "kg"; "100 g" stays
    const value = right.trim().split('/')[0].trim().replace('.', ',');
    return unit && value ? `${value} €/${unit}` : null;
  }
  // Already "<value> €/<unit>" (e.g. "22.79 €/kg", "0.46 €/Stk.").
  const m = ppu.match(/(-?\d+(?:[.,]\d+)?)\s*€?\s*\/\s*(\S+)/);
  if (!m) return null;
  const value = m[1].replace('.', ',');
  const unit = m[2].replace(/[.,]$/, ''); // drop a trailing "." in "Stk."
  return `${value} €/${unit}`;
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

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Compact "as of" label for a cached-deals timestamp (device-local): "just now",
 * "5m ago", "9:14" (today), "Mon 9:00" (this week), "18 Jun" (older).
 */
export const fmtAsOf = (ts: number | null): string => {
  if (ts == null) return '';
  const now = new Date();
  const d = new Date(ts);
  const diffMs = now.getTime() - ts;
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hhmm = `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
  if (d.toDateString() === now.toDateString()) return hhmm;
  if (diffMs < 7 * 24 * 60 * 60 * 1000) return `${DAYS[d.getDay()]} ${hhmm}`;
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`;
};

// Sunday 23:59:59.999 (device-local) of the week containing `ts` — German weekly
// flyers expire by Sunday, so this is when the cached deals stop being current.
function endOfDealWeek(ts: number): number {
  const d = new Date(ts);
  const daysUntilSunday = (7 - d.getDay()) % 7; // getDay: 0=Sun..6=Sat; 0 if already Sun
  const sunday = new Date(d);
  sunday.setDate(d.getDate() + daysUntilSunday);
  sunday.setHours(23, 59, 59, 999);
  return sunday.getTime();
}

/** True once the cached deals are past their weekly (Sunday) expiry. */
export const dealsStale = (cachedAt: number | null): boolean =>
  cachedAt != null && Date.now() > endOfDealWeek(cachedAt);

/** Today's device-local date as "YYYY-MM-DD" (compares directly with offer.valid_from/to). */
export const todayISO = (): string => {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};
