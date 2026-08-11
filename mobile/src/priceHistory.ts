/**
 * Price trail for History rows — the weekly series from the `grocery-price-history`
 * collector, projected down to what this device actually needs.
 *
 * **The design is dictated by one measurement: 93.75% of the collector's 6,588 products
 * have exactly ONE data point** (>=2 weeks: 6.25%, >=3: 0.76%). A chart would be a single
 * dot for almost everything, so nothing here renders a "trend" it cannot support — the row
 * is TIERED BY EVIDENCE, and tier 0 deliberately renders *nothing at all*. A "no history
 * yet" placeholder on 94% of rows would teach the user the feature is broken, and the row
 * is already complete without it (paid-vs-now is local and needs no fetch).
 *
 * This module is pure: no fetch, no storage, no React. `usePriceHistory` owns the network.
 */
import { nameKey } from './nameKey';
import { HistoryItem } from './types';

/** One weekly observation: [ISO week, price in cents, unit price in cents | null]. */
export type PricePoint = { week: string; cents: number; unitCents: number | null };

/** The collector's history-relative judgement. `new` means "not enough weeks to judge". */
export type Verdict = 'new' | 'typical' | 'worse' | 'true_low';

/** One product's history, as projected from the index. */
export type PriceFacts = {
  /** The chain this series actually came from — NOT necessarily the item's own chain. */
  chain: string;
  /** The collector's own label. Shown when it differs from the stored name: that is the
   *  audit trail for a bad `name_key` collapse (which is how the Coca-Cola noise was found). */
  label: string;
  series: PricePoint[];
  /** From the source `stats`, NOT `series.length` — the series is capped for storage. */
  weeksSeen: number;
  min: number;
  median: number;
  max: number;
  last: number;
  verdict: Verdict;
};

/**
 * Newest N points kept per product. The cap is a STORAGE budget, so `min`/`median`/`max`
 * must keep coming from the source stats (computed over the full series) — truncating a
 * series must never turn "cheapest ever" into "cheapest recently".
 */
export const MAX_POINTS = 8;

/**
 * Above this max/min ratio the stats are not describing one product. `name_key` collapses
 * pack variants, so `edeka_center "coca cola"` runs 399·69·149·1169·799 cents — can vs
 * bottle vs crate. Measured: this catches 29 of the 412 multi-week products.
 */
export const NOISE_RATIO = 4;

const shortWeek = (week: string): string => week.replace(/^\d{4}-/, '');

/** Raw index entry, as the collector emits it (schema 1). */
type RawEntry = {
  chain?: unknown;
  name_key?: unknown;
  label?: unknown;
  series?: unknown;
  stats?: { min?: unknown; median?: unknown; max?: unknown; last?: unknown; weeks_seen?: unknown };
  verdict?: unknown;
};

const num = (v: unknown): number | null => (typeof v === 'number' && isFinite(v) ? v : null);

function toFacts(raw: RawEntry): PriceFacts | null {
  const chain = typeof raw.chain === 'string' ? raw.chain : null;
  const stats = raw.stats ?? {};
  const min = num(stats.min);
  const median = num(stats.median);
  const max = num(stats.max);
  const last = num(stats.last);
  if (!chain || min === null || median === null || max === null || last === null) return null;

  const points: PricePoint[] = [];
  for (const p of Array.isArray(raw.series) ? raw.series : []) {
    if (!Array.isArray(p)) continue;
    const week = typeof p[0] === 'string' ? p[0] : null;
    const cents = num(p[1]);
    if (week === null || cents === null) continue;
    points.push({ week, cents, unitCents: num(p[2]) });
  }
  if (points.length === 0) return null;

  return {
    chain,
    label: typeof raw.label === 'string' ? raw.label : '',
    // newest last; keep the most RECENT MAX_POINTS
    series: points.slice(-MAX_POINTS),
    weeksSeen: num(stats.weeks_seen) ?? points.length,
    min,
    median,
    max,
    last,
    verdict:
      raw.verdict === 'typical' || raw.verdict === 'worse' || raw.verdict === 'true_low'
        ? raw.verdict
        : 'new',
  };
}

/**
 * What gets persisted: the PROJECTION, never the index.
 *
 * Storing the projection keeps the cache small (a 100-item History is roughly 20 KB) AND
 * makes the misses durable, which is what stops the no-history case from refetching on
 * every open.
 */
export type CachedPriceHistory = {
  byKey: Record<string, PriceFacts[]>;
  /**
   * Keys proven absent from this index revision.
   *
   * Since the switch to `index-min.json` this means one of TWO things, and nothing in the
   * app can tell them apart: the collector has never seen the product, OR it has seen it in
   * exactly one week and the publisher withheld it. Both are correctly tier 0 (render
   * nothing), so the ambiguity costs nothing at display time — the evidence for the second
   * case is the row the filter removed.
   *
   * What it does change is refetch economics. A miss now flips to a hit the moment a product
   * is seen a SECOND week, which is precisely the event this feature exists to surface. The
   * cadences line up: the upstream regenerates Sunday 09:00 UTC and `dealsStale` turns over
   * on the same weekly boundary, so the transition is picked up on the next open after the
   * flyer week rolls — not held for an arbitrary window.
   */
  misses: string[];
  /** The weeks the index covered, for "N weeks of data" context. */
  weeks: string[];
  /** The index's own `generated_at`. */
  generatedAt: string;
  /** Sent back as `If-None-Match`; a 304 proves the misses are still misses, at 0 bytes. */
  etag: string | null;
  fetchedAt: number;
  /**
   * Which upstream file this projection came from. A cache written against a different
   * source has `misses` computed under a different policy and an `etag` belonging to a
   * different URL, so it must be DISCARDED rather than reused — see `CACHE_SOURCE`.
   *
   * Optional so a pre-switch cache parses; `undefined` simply never matches, which is the
   * behaviour we want.
   */
  source?: string;
};

/**
 * Identifies the upstream file + policy a cached projection was built from. Bump it whenever
 * INDEX_URL changes or the publisher changes what it includes.
 *
 * Without this, a device holding a pre-switch cache would send an ETag from the OLD url to
 * the new one and, worse, keep serving `misses` that meant "absent from the full index" as
 * though they meant "absent from the filtered one". Those are different questions.
 */
export const CACHE_SOURCE = 'index-min@1';

/**
 * The cached projection, but only if it was built from the file we are about to ask for.
 *
 * Exported and pure so it is testable: this is the whole safety mechanism behind switching
 * upstream files, and inline in the hook it would only be exercised by a fetch test that
 * does not exist. Returns `null` for a mismatch, which the caller treats as "no cache" —
 * so the stale `misses` and the ETag from the old URL are both dropped.
 */
export function usableCache(stored: CachedPriceHistory | null): CachedPriceHistory | null {
  return stored?.source === CACHE_SOURCE ? stored : null;
}

export type Projection = {
  /** name_key -> every chain's series for that product. */
  byKey: Record<string, PriceFacts[]>;
  /** Keys we looked up and the index genuinely does not have. Not optional: without it
   *  there is no way to tell "absent" from "never looked up", so 94% of rows would refetch
   *  forever. */
  misses: string[];
};

/**
 * Keep only the entries matching `keys`, discard the rest. `index-min.json` is 389 KB
 * decompressed (65 KB over the wire); a 100-item History projects to roughly 20 KB, which is what gets
 * persisted. Parsing happens once, in memory, and the parsed index is never stored.
 */
export function projectIndex(raw: unknown, keys: string[]): Projection {
  const wanted = new Set(keys);
  const byKey: Record<string, PriceFacts[]> = {};
  const products = (raw as { products?: unknown })?.products;

  for (const entry of Array.isArray(products) ? products : []) {
    const e = entry as RawEntry;
    const key = typeof e?.name_key === 'string' ? e.name_key : null;
    if (key === null || !wanted.has(key)) continue;
    const facts = toFacts(e);
    if (facts === null) continue;
    (byKey[key] ||= []).push(facts);
  }

  return { byKey, misses: keys.filter((k) => byKey[k] === undefined) };
}

/**
 * Chain-first, with a cross-chain fallback the caller can LABEL.
 *
 * Deliberately not a union across chains: the index keeps a per-(chain, week) minimum, so a
 * union's per-week value would be a min-of-mins that nobody ever saw on a shelf.
 */
export function joinHistory(
  item: HistoryItem,
  byKey: Record<string, PriceFacts[]>,
): { facts: PriceFacts; crossChain: boolean } | null {
  const candidates = byKey[nameKey(item.name)];
  if (!candidates || candidates.length === 0) return null;
  const own = candidates.find((c) => c.chain === item.chain);
  if (own) return { facts: own, crossChain: false };
  return { facts: candidates[0], crossChain: true };
}

/** What a History row should draw. Tier 0 draws nothing — see the module docstring. */
export type PriceTrail =
  | { tier: 0 }
  | {
      tier: 1;
      chain: string;
      crossChain: boolean;
      label: string;
      cents: number;
      week: string;
    }
  | {
      tier: 2;
      chain: string;
      crossChain: boolean;
      label: string;
      weeksSeen: number;
      firstCents: number;
      lastCents: number;
      /** Signed % change first->last; null when the first point is 0. */
      deltaPct: number | null;
    }
  | {
      tier: 3;
      chain: string;
      crossChain: boolean;
      label: string;
      weeksSeen: number;
      series: PricePoint[];
      min: number;
      median: number;
      max: number;
      minWeek: string | null;
      /** Every observation is the same price — "always X" beats a vacuous "low X · usual X". */
      flat: boolean;
      /** max/min >= NOISE_RATIO: pack variants collapsed together. Stats are suppressed. */
      noisy: boolean;
      /** Only when it is worth stating. `new` is excluded IN THE TYPE, not just by the
       *  builder: it means "not enough weeks to judge", so rendering it as a verdict
       *  would dress an absence of evidence up as a finding. */
      verdict: Exclude<Verdict, 'new'> | null;
      /** Today's price as a % of the usual (median), computed from the LIVE offer so it
       *  stays right when today's deal postdates the index. Null when nothing is on sale. */
      todayPctOfUsual: number | null;
    };

export const NO_TRAIL: PriceTrail = { tier: 0 };

/**
 * Derive what to draw. `todayCents` is the live matched price, not an index value.
 */
export function buildTrail(
  joined: { facts: PriceFacts; crossChain: boolean } | null,
  todayCents: number | null = null,
): PriceTrail {
  if (joined === null) return NO_TRAIL;
  const { facts, crossChain } = joined;
  const { chain, label, series, weeksSeen, min, median, max } = facts;
  const common = { chain, crossChain, label };

  // Seen once: state the single observation and stop. No delta (nothing to compare), no
  // verdict (mechanically `new`), no chart (one dot).
  if (weeksSeen <= 1 || series.length < 2) {
    const only = series[series.length - 1];
    return { tier: 1, ...common, cents: only.cents, week: shortWeek(only.week) };
  }

  if (weeksSeen === 2) {
    const first = series[0].cents;
    const last = series[series.length - 1].cents;
    return {
      tier: 2,
      ...common,
      weeksSeen,
      firstCents: first,
      lastCents: last,
      deltaPct: first > 0 ? Math.round(((last - first) / first) * 100) : null,
    };
  }

  const flat = min === max;
  const noisy = min > 0 && max / min >= NOISE_RATIO;
  const lowest = series.reduce((a, b) => (b.cents < a.cents ? b : a), series[0]);
  return {
    tier: 3,
    ...common,
    weeksSeen,
    series,
    min,
    median,
    max,
    // Only meaningful if the capped window actually contains the all-time low.
    minWeek: lowest.cents === min ? shortWeek(lowest.week) : null,
    flat,
    noisy,
    verdict: noisy || facts.verdict === 'new' ? null : facts.verdict,
    todayPctOfUsual:
      todayCents !== null && !noisy && median > 0 ? Math.round((todayCents / median) * 100) : null,
  };
}

/** Convenience: join + build in one call. */
export function trailFor(
  item: HistoryItem,
  byKey: Record<string, PriceFacts[]>,
  todayCents: number | null = null,
): PriceTrail {
  return buildTrail(joinHistory(item, byKey), todayCents);
}
