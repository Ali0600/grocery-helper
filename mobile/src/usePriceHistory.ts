/**
 * Fetches the price-history index and projects it down to this device's History items.
 *
 * Runs ONLY while the History sheet is open. It is deliberately not part of
 * `prefetchDetailData`: that is gated on (plz, count) and serves a page everyone opens,
 * whereas this is a 418 KB download for a page most sessions never visit. `DealsScreen`
 * therefore has no diff for this feature.
 */
import { useEffect, useRef, useState } from 'react';

import { DEFAULT_PLZ } from './config';
import { dealsStale } from './format';
import { nameKey } from './nameKey';
import { CachedPriceHistory, projectIndex } from './priceHistory';
import { getPriceHistory, getStoredPlz, setPriceHistory } from './storage';
import { HistoryItem } from './types';

const INDEX_URL =
  'https://raw.githubusercontent.com/Ali0600/grocery-price-history/main/data/index.json';

/**
 * Tripwire on the COMPRESSED body, checked before `res.json()` — parsing is what breaks on
 * a phone, and by the time you are parsing it is too late to decline.
 *
 * The index grows ~1,300 products/week at a flat ~419 B each, so the decompressed size is
 * projected to reach ~14 MB by week 26 and ~28 MB by week 52. At the measured ~6.6:1 gzip
 * ratio this ceiling corresponds to roughly the week-26 mark: the point at which the real
 * fix (an upstream index of only `weeks_seen >= 2` products — 412 rows today, ~170 KB) is
 * needed rather than optional. Tripping this degrades the trail; it never breaks History.
 */
export const MAX_INDEX_BYTES = 2_500_000;

const FETCH_TIMEOUT_MS = 30_000;

/**
 * The collector's only region is `berlin`. Outside it every lookup would miss, so the
 * honest thing is not to spend the download at all — and certainly not to show a Hamburg
 * user Berlin's price history.
 */
export const isCoveredPlz = (plz: string): boolean => {
  const n = Number(plz);
  return Number.isInteger(n) && n >= 10115 && n <= 14199;
};

export type PriceHistoryState = {
  cache: CachedPriceHistory | null;
  loading: boolean;
};

/** Keys this History needs that the cache can neither answer nor rule out. */
function unknownKeys(items: HistoryItem[], cache: CachedPriceHistory | null): string[] {
  const keys = Array.from(new Set(items.map((i) => nameKey(i.name)).filter(Boolean)));
  if (!cache) return keys;
  const known = new Set(cache.misses);
  return keys.filter((k) => cache.byKey[k] === undefined && !known.has(k));
}

/**
 * The PLZ is read from storage rather than passed in, so `DealsScreen` needs no change for
 * this feature at all — the hook owns every input it has, which is the point of putting the
 * network here instead of in the deals prefetch.
 */
export function usePriceHistory(visible: boolean, items: HistoryItem[]) {
  const [state, setState] = useState<PriceHistoryState>({ cache: null, loading: false });
  // One in-flight fetch per mount, and never a second pass for the same open.
  const running = useRef(false);

  useEffect(() => {
    if (!visible || running.current) return;
    let cancelled = false;
    running.current = true;

    (async () => {
      const cached = await getPriceHistory();
      if (!cancelled) setState({ cache: cached, loading: false });
      // Fall back to DEFAULT_PLZ, not to "" — the stored PLZ is only written once the user
      // changes it, so `null` is the NORMAL first-run state and treating it as uncovered
      // silently disabled this whole feature for everyone who never touched the pin.
      if (!isCoveredPlz((await getStoredPlz()) ?? DEFAULT_PLZ)) return;

      const missing = unknownKeys(items, cached);
      const stale = !cached || dealsStale(cached.fetchedAt);
      if (missing.length === 0 && !stale) return; // fully answerable offline

      // `If-None-Match` is sent ONLY when we are refreshing staleness and every key is
      // already accounted for. A 304 proves the index is BYTE-IDENTICAL to the one we
      // projected — it does NOT prove anything about a key we never looked up, because
      // the projection discarded every entry we did not ask for. So a mid-week addition
      // has to re-download the body; conditional-GET can't answer a question the cached
      // projection never asked.
      //
      // Measured gotcha: raw.githubusercontent issues a DIFFERENT ETag per content
      // encoding — `W/"1b9edb…"` for gzip, `"51c815…"` plain — so the stored one only
      // revalidates against a request with the same encoding. `fetch` always asks for
      // gzip here, so it round-trips; hand-testing with curl and no `--compressed`
      // returns a full 200 and looks like the server ignoring the header.
      const conditional = missing.length === 0 && cached?.etag != null;

      if (!cancelled) setState({ cache: cached, loading: true });
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
      try {
        const res = await fetch(INDEX_URL, {
          signal: controller.signal,
          headers: conditional ? { 'If-None-Match': cached!.etag! } : undefined,
        });

        if (res.status === 304 && cached) {
          // Unchanged: the existing projection, misses included, is still correct.
          const bumped = { ...cached, fetchedAt: Date.now() };
          await setPriceHistory(bumped);
          if (!cancelled) setState({ cache: bumped, loading: false });
          return;
        }
        if (!res.ok) throw new Error(`price index HTTP ${res.status}`);

        const len = Number(res.headers.get('content-length'));
        if (Number.isFinite(len) && len > MAX_INDEX_BYTES) {
          throw new Error(`price index too large (${len} bytes) — refusing to parse`);
        }

        const raw = await res.json();
        // Project against ALL current keys, not just the missing ones: the index has been
        // rebuilt, so previously-cached series are stale too.
        const keys = Array.from(new Set(items.map((i) => nameKey(i.name)).filter(Boolean)));
        const { byKey, misses } = projectIndex(raw, keys);
        const next: CachedPriceHistory = {
          byKey,
          misses,
          weeks: Array.isArray(raw?.weeks) ? raw.weeks.filter((w: unknown) => typeof w === 'string') : [],
          generatedAt: typeof raw?.generated_at === 'string' ? raw.generated_at : '',
          etag: res.headers.get('etag'),
          fetchedAt: Date.now(),
        };
        await setPriceHistory(next);
        if (!cancelled) setState({ cache: next, loading: false });
      } catch (e) {
        // Never block History on this: the row's paid-vs-now spine is local and complete.
        console.warn('priceHistory: fetch failed, keeping the cached projection', e);
        if (!cancelled) setState({ cache: cached, loading: false });
      } finally {
        clearTimeout(timer);
      }
    })();

    return () => {
      cancelled = true;
    };
    // `items` intentionally omitted: re-running on every History mutation would refetch a
    // 418 KB index mid-interaction. The sheet is remounted on each open, which is when a
    // newly-added item gets picked up.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);

  return state;
}
