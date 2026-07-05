import {
  CategoryCount,
  NearbyStore,
  Offer,
  OfferPayload,
  ResetResult,
  ScrapeResult,
  Store,
} from './types';

// Default to the deployed backend so device + OTA builds work out of the box. Override
// via mobile/.env (EXPO_PUBLIC_API_URL) for local dev — e.g. http://localhost:8001, or
// your Mac's LAN IP on a physical phone. The default matters because `eas update` does
// NOT read eas.json's build-profile `env`, so production OTA bundles fall back to this.
const BASE = process.env.EXPO_PUBLIC_API_URL ?? 'https://grocery-helper-sw6c.onrender.com';

// Optional token for the destructive server reset; only needed if the backend sets
// ADMIN_TOKEN. It rides in the public bundle, so it's a light guard against drive-by hits,
// not a real secret. Leave unset for an open reset (matching /api/scrape).
const ADMIN_TOKEN = process.env.EXPO_PUBLIC_ADMIN_TOKEN;

// A sleeping / redeploying free-tier backend times out or returns a 5xx the first time, then
// succeeds once it's awake — so those are retried. A thrown `API 4xx` is a real client error
// and is NOT retried. Exported for tests.
export function isRetryable(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  if (err.name === 'AbortError') return true; // our timeout fired (likely a cold start)
  if (/^API 5\d\d$/.test(err.message)) return true; // gateway / boot 5xx
  if (err.message.startsWith('API ')) return false; // any other status (4xx) — a real error
  return true; // network-level fetch failure — server unreachable / waking
}

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

// Abort a request after `timeoutMs` so a sleepy free-tier cold start fails fast instead of
// hanging the UI. On a cold-start-shaped failure, retry (short backoff) up to `retries` times
// so a waking backend recovers itself rather than surfacing an error to the user.
async function request<T>(
  path: string,
  init: RequestInit,
  timeoutMs: number,
  retries: number,
): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${BASE}${path}`, { ...init, signal: controller.signal });
      if (!res.ok) throw new Error(`API ${res.status}`);
      return (await res.json()) as T;
    } catch (err) {
      if (attempt >= retries || !isRetryable(err)) throw err;
    } finally {
      clearTimeout(timer);
    }
    await delay(800 * (attempt + 1)); // brief backoff before the next wake-up attempt
  }
}

// Reads retry twice — a cold start often needs a couple attempts to wake the backend. Writes
// (scrape/reset) already use long timeouts, so one retry is enough of a safety net.
const get = <T>(path: string, timeoutMs = 30000, retries = 2): Promise<T> =>
  request<T>(path, {}, timeoutMs, retries);
const post = <T>(
  path: string,
  timeoutMs = 30000,
  headers?: Record<string, string>,
  retries = 1,
): Promise<T> =>
  request<T>(path, { method: 'POST', ...(headers ? { headers } : {}) }, timeoutMs, retries);

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

  // The full raw source payload of one offer (flyer content / Lidl coupon dict), for the
  // "View payload" view in the deal detail. `payload` is null if not captured yet.
  offerPayload(id: number) {
    return get<OfferPayload>(`/api/offers/${id}/payload`);
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

  // Wipe the backend's stored offers and re-scrape this PLZ from scratch (Options →
  // "Wipe & re-scrape server DB"). Destructive on the server; same generous timeout as
  // scrape. The token rides in an X-Admin-Token header (not the query string, which
  // would land in server access logs).
  resetDb(plz: string) {
    const q = new URLSearchParams({ plz });
    return post<ResetResult>(
      `/api/reset?${q.toString()}`,
      120000,
      ADMIN_TOKEN ? { 'X-Admin-Token': ADMIN_TOKEN } : undefined,
    );
  },
};
