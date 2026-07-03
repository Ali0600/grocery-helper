// The "Mit App" headline. EDEKA / E center flyer offers can carry an app-exclusive price
// (Offer.app_price_cents) that undercuts the guaranteed flyer price. When one is present the app
// treats it as the headline: the app price becomes the main price and its (deeper) discount the
// main badge, with the flyer/regular price struck through. Pure so it's unit-tested and shared by
// OfferCard (display) and compareOffers (the "biggest discount" sort). All four price fields
// already ship in OfferOut, so this is display-only — no backend/optimizer involvement.
import { Offer } from './types';

/** True when the offer has a usable app-exclusive price strictly below the flyer price. */
export function hasAppDeal(o: Offer): boolean {
  return o.app_price_cents != null && o.app_price_cents < o.price_cents;
}

/** Headline price: the app price for a Mit-App deal, otherwise the flyer price. */
export function headlinePriceCents(o: Offer): number {
  return hasAppDeal(o) ? (o.app_price_cents as number) : o.price_cents;
}

/**
 * The "before" price struck through under the headline. For a Mit-App deal that's the higher of
 * the regular price (if any) or the flyer price; for a normal offer it's the regular price (or
 * null when there isn't one).
 */
export function headlineStrikeCents(o: Offer): number | null {
  if (hasAppDeal(o)) return o.regular_price_cents ?? o.price_cents;
  return o.regular_price_cents;
}

/**
 * The headline discount %. For a Mit-App deal it's the app price's discount off its strike base
 * (regular if present, else the flyer price) so the badge matches the shown price and strike; for
 * a normal offer it's the stored discount_pct unchanged. Null when there's no positive discount.
 */
export function headlineDiscountPct(o: Offer): number | null {
  if (!hasAppDeal(o)) return o.discount_pct;
  const base = o.regular_price_cents ?? o.price_cents;
  const app = o.app_price_cents as number;
  if (base <= app) return null;
  return Math.round(((base - app) / base) * 100);
}
