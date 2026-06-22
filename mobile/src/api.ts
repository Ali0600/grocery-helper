import { CategoryCount, NearbyStore, Offer, ScrapeResult, Store } from './types';

// Default to the deployed backend so device + OTA builds work out of the box. Override
// via mobile/.env (EXPO_PUBLIC_API_URL) for local dev — e.g. http://localhost:8001, or
// your Mac's LAN IP on a physical phone. The default matters because `eas update` does
// NOT read eas.json's build-profile `env`, so production OTA bundles fall back to this.
const BASE = process.env.EXPO_PUBLIC_API_URL ?? 'https://grocery-helper-sw6c.onrender.com';

// Abort a request after `timeoutMs` so a sleepy free-tier cold start fails fast (and can
// fall back to an on-demand scrape) instead of hanging the UI for minutes.
async function request<T>(path: string, init: RequestInit, timeoutMs: number): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE}${path}`, { ...init, signal: controller.signal });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

const get = <T>(path: string, timeoutMs = 30000): Promise<T> => request<T>(path, {}, timeoutMs);
const post = <T>(path: string, timeoutMs = 30000): Promise<T> =>
  request<T>(path, { method: 'POST' }, timeoutMs);

export const api = {
  base: BASE,

  // Load the whole PLZ set; the app does category/search/non-food filtering
  // client-side, so search covers every deal (not just the top-ranked ones).
  // Two chains (Lidl + REWE) push a Berlin PLZ past ~1300 offers, so the limit
  // is generous; if a 3rd chain pushes a PLZ over this, move search server-side
  // (a `q` param on /api/offers) rather than raising it further.
  offers(params: { plz?: string; sort?: 'discount' | 'price' } = {}) {
    const q = new URLSearchParams();
    if (params.plz) q.set('plz', params.plz);
    q.set('sort', params.sort ?? 'discount');
    q.set('limit', '2000');
    return get<Offer[]>(`/api/offers?${q.toString()}`);
  },

  categories(plz?: string) {
    const q = new URLSearchParams();
    if (plz) q.set('plz', plz);
    return get<CategoryCount[]>(`/api/categories?${q.toString()}`);
  },

  stores() {
    return get<Store[]>('/api/stores');
  },

  // Nearest store of each known chain around the PLZ (OSM); active=true for
  // chains we scrape deals for. Empty list => store data was unreachable.
  nearbyStores(plz?: string) {
    const q = new URLSearchParams();
    if (plz) q.set('plz', plz);
    return get<NearbyStore[]>(`/api/nearby-stores?${q.toString()}`);
  },

  // Every branch of one chain near the PLZ (nearest first) — the "Change" picker,
  // so the user can choose the store actually near them, not just nearest the PLZ.
  chainBranches(plz: string | undefined, chain: string) {
    const q = new URLSearchParams();
    if (plz) q.set('plz', plz);
    q.set('chain', chain);
    return get<NearbyStore[]>(`/api/nearby-stores?${q.toString()}`);
  },

  // Scrape the nearest store for a PLZ on demand and return the resolved store(s).
  // A cold start + full scrape is slow, so allow a generous timeout.
  scrape(plz: string) {
    return post<ScrapeResult>(`/api/scrape?plz=${encodeURIComponent(plz)}`, 120000);
  },
};
