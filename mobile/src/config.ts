/**
 * App-level constants that more than one module needs.
 *
 * `DEFAULT_PLZ` lives here rather than in `DealsScreen` because it is now read by two
 * unrelated places (the deals screen and the price-history fetch), and a duplicated default
 * would be a second source of truth for the one constant this repo must never get wrong:
 * the committed value is a NEUTRAL central-Berlin code, and a personal postal code belongs
 * only in gitignored `mobile/.env` (`EXPO_PUBLIC_DEFAULT_PLZ`). See CLAUDE.md.
 */
export const DEFAULT_PLZ = process.env.EXPO_PUBLIC_DEFAULT_PLZ ?? '10115';
