/**
 * The app's two top-level sections: Grocery and Drugstore.
 *
 * Mirrors `backend/app/verticals.py`, but deliberately holds NO chain list. The backend
 * already scopes `/api/offers` and `/api/categories` by `vertical`, so a second copy of
 * "which chains are grocery" here would be a source of truth that can only drift. Mobile
 * needs the slug (to pass through) and the label (to render) — nothing else.
 */
import type { IconName } from './components/Icon';

export type Vertical = 'grocery' | 'drugstore';

/** Display order on the home screen. */
export const VERTICALS: readonly Vertical[] = ['grocery', 'drugstore'] as const;

export const VERTICAL_LABELS: Record<Vertical, string> = {
  grocery: 'Grocery',
  drugstore: 'Drugstore',
};

/**
 * Shown under the label on the home screen only when that vertical has no cached deals
 * yet — once it does, the card shows the real deal count instead, which can't go stale
 * the way a hardcoded chain list would.
 */
export const VERTICAL_BLURBS: Record<Vertical, string> = {
  grocery: 'Supermarket flyer deals',
  drugstore: 'Drogerie, beauty & household',
};

export const VERTICAL_ICONS: Record<Vertical, IconName> = {
  grocery: 'cart',
  drugstore: 'sparkles',
};

/** Recipes are authored from grocery ingredients, so that surface is grocery-only. */
export const hasRecipes = (v: Vertical): boolean => v === 'grocery';

/** Narrow an untrusted string (a persisted value, a deep link) to a known vertical. */
export function asVertical(value: unknown): Vertical | null {
  return typeof value === 'string' && (VERTICALS as readonly string[]).includes(value)
    ? (value as Vertical)
    : null;
}
