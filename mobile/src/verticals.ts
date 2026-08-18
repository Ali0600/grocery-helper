/**
 * The app's three top-level sections: Grocery, Drinks and Drugstore.
 *
 * Mirrors `backend/app/verticals.py`, but deliberately holds NO chain or category list.
 * The backend already scopes `/api/offers` and `/api/categories` by `vertical`, so a
 * second copy of "which chains are grocery" — or, since Drinks, "which categories are
 * drinks" — would be a source of truth that can only drift. Mobile needs the slug (to
 * pass through) and the label (to render) — nothing else.
 *
 * A section this app knows but the deployed backend does not gets a **422**, not a
 * fallback: the param is a pattern built from the backend's own registry. So a new
 * section ships backend-first, and the OTA follows once it serves.
 */
import type { IconName } from './components/Icon';

export type Vertical = 'grocery' | 'drinks' | 'drugstore';

/** Display order on the home screen. */
export const VERTICALS: readonly Vertical[] = ['grocery', 'drinks', 'drugstore'] as const;

export const VERTICAL_LABELS: Record<Vertical, string> = {
  grocery: 'Grocery',
  drinks: 'Drinks',
  drugstore: 'Drugstore',
};

/**
 * Shown under the label on the home screen only when that vertical has no cached deals
 * yet — once it does, the card shows the real deal count instead, which can't go stale
 * the way a hardcoded chain list would.
 */
export const VERTICAL_BLURBS: Record<Vertical, string> = {
  grocery: 'Supermarket flyer deals',
  drinks: 'Soft drinks, beer, wine & spirits',
  drugstore: 'Drogerie, beauty & household',
};

export const VERTICAL_ICONS: Record<Vertical, IconName> = {
  grocery: 'cart',
  drinks: 'beer',
  drugstore: 'sparkles',
};

/** Recipes are authored from grocery ingredients, so that surface is grocery-only. */
export const hasRecipes = (v: Vertical): boolean => v === 'grocery';

/**
 * The section whose deals belong on the same shopping trip as this one's — or `null`.
 *
 * Grocery and Drinks are the SAME six supermarkets, split only by category, so a beer and
 * a loaf of bread are one trip: the Basket, Recipes and History match against both. The
 * drugstore chains are a different errand, which is the whole reason this returns `null`
 * for them — merging there would be as wrong as not merging here.
 *
 * Only the shared surfaces merge. The deals list, the category chips, Compare and the
 * "My Categories" home stay scoped to the section you are standing in — that is what the
 * user asked for ("I'm just looking for food and it's distracting").
 */
export function companionVertical(v: Vertical): Vertical | null {
  if (v === 'grocery') return 'drinks';
  if (v === 'drinks') return 'grocery';
  return null;
}

/** Narrow an untrusted string (a persisted value, a deep link) to a known vertical. */
export function asVertical(value: unknown): Vertical | null {
  return typeof value === 'string' && (VERTICALS as readonly string[]).includes(value)
    ? (value as Vertical)
    : null;
}
