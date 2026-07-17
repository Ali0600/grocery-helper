// Pure core for "Hide": the deal detail can dismiss an offer you're not interested in, and it
// disappears from the deals list (and from Basket/Recipes/Compare) — it is NOT demoted to the
// "More" bucket, it's gone.
//
// Scope of one hide (the user's choice): THIS CHAIN's copy, THIS flyer week.
//   * per-chain — hiding Edeka's Schnaps leaves Lidl's Schnaps visible, so the key carries the
//     chain alongside the normalized product name;
//   * one week — it comes back when the flyers refresh.
//
// Why not key on `offer.id`, the obvious "this exact offer" handle: ids are NOT stable here.
// `/api/reset` deletes every Offer row and re-scrapes, and Render's SQLite is ephemeral, so a
// cold start rebuilds the table from scratch — SQLite reuses rowids after a full delete, so the
// same id is a DIFFERENT product next week. Keying on it would un-hide what you hid *and*
// silently hide something you didn't. (types.ts says the same thing: ids churn weekly, which is
// why likes.ts avoids them too.) Identity + an explicit expiry is stable under re-scrapes.
//
// No React/RN imports → unit-testable.
import { normName } from './edekaVs';
import { dealsStale } from './format';
import { Offer } from './types';

/** A hidden offer, persisted by identity rather than by id. */
export type HiddenItem = {
  key: string; // `${chain}:${normName(name)}` — per-chain product identity
  name: string; // as displayed when hidden (for a future "hidden deals" listing)
  chain: string;
  hiddenAt: number; // Date.now() — drives the one-flyer-week expiry
};

/** The stable identity of a hidden offer. One definition, used to persist a hide and to ask
 * "is this hidden?" — don't call `resolveHidden` just to read a key, it stamps `Date.now()`. */
export const hideKey = (offer: Offer): string => `${offer.chain}:${normName(offer.name)}`;

/** Snapshot an offer as a persistable hide. */
export function resolveHidden(offer: Offer): HiddenItem {
  return { key: hideKey(offer), name: offer.name, chain: offer.chain, hiddenAt: Date.now() };
}

/** The hides that still apply: a hide lasts for the flyer week it was made in, so anything from
 * a previous week has expired and the deal is visible again. Reuses the deals cache's weekly
 * expiry (`dealsStale` → past the Sunday of that week) rather than inventing a second rule.
 * EVERY read path goes through this, so an expired hide can never leak into a filter. */
export const activeHidden = (items: HiddenItem[]): HiddenItem[] =>
  items.filter((h) => !dealsStale(h.hiddenAt));

/** Active hide keys, for O(1) lookups while filtering a few thousand offers. */
export const hiddenKeySet = (items: HiddenItem[]): Set<string> =>
  new Set(activeHidden(items).map((h) => h.key));

/** Is this offer currently hidden? */
export const isHidden = (offer: Offer, items: HiddenItem[]): boolean =>
  hiddenKeySet(items).has(hideKey(offer));

/** Drop hidden offers (the normal case). */
export const filterHidden = (offers: Offer[], keys: Set<string>): Offer[] =>
  keys.size === 0 ? offers : offers.filter((o) => !keys.has(hideKey(o)));

/** Keep ONLY hidden offers — the Filters sheet's "Show hidden" lens, which is the only way back
 * to a hidden deal's detail (and so to its Un-Hide button). */
export const onlyHidden = (offers: Offer[], keys: Set<string>): Offer[] =>
  offers.filter((o) => keys.has(hideKey(o)));

/** Add/remove a hide, pruning expired entries so the stored list can't grow forever. */
export function toggleHidden(items: HiddenItem[], offer: Offer): HiddenItem[] {
  const key = hideKey(offer);
  const live = activeHidden(items);
  return live.some((h) => h.key === key)
    ? live.filter((h) => h.key !== key)
    : [...live, resolveHidden(offer)];
}
