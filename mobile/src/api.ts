import { CategoryCount, NearbyStore, Offer, ScrapeResult, Store } from './types';

// Override per-environment via mobile/.env (EXPO_PUBLIC_API_URL). On a physical
// phone, localhost won't resolve — set this to your machine's LAN IP.
const BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return (await res.json()) as T;
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return (await res.json()) as T;
}

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
  scrape(plz: string) {
    return post<ScrapeResult>(`/api/scrape?plz=${encodeURIComponent(plz)}`);
  },
};
