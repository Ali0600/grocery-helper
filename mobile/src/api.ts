import { CategoryCount, Offer, ScrapeResult, Store } from './types';

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
  offers(params: { plz?: string; sort?: 'discount' | 'price' } = {}) {
    const q = new URLSearchParams();
    if (params.plz) q.set('plz', params.plz);
    q.set('sort', params.sort ?? 'discount');
    q.set('limit', '1000');
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

  // Scrape the nearest store for a PLZ on demand and return the resolved store(s).
  scrape(plz: string) {
    return post<ScrapeResult>(`/api/scrape?plz=${encodeURIComponent(plz)}`);
  },
};
