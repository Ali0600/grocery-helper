import { CategoryCount, Offer } from './types';

// Override per-environment via mobile/.env (EXPO_PUBLIC_API_URL). On a physical
// phone, localhost won't resolve — set this to your machine's LAN IP.
const BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  base: BASE,

  offers(params: { category?: string; sort?: 'discount' | 'price' } = {}) {
    const q = new URLSearchParams();
    if (params.category) q.set('category', params.category);
    q.set('sort', params.sort ?? 'discount');
    q.set('limit', '200');
    return get<Offer[]>(`/api/offers?${q.toString()}`);
  },

  categories() {
    return get<CategoryCount[]>('/api/categories');
  },
};
