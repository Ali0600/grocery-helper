// Dark-theme design tokens. `colors` is kept (many components import it); new/edited
// code should also use `space`, `radius`, `font`, and `tint` so spacing, corners, type,
// and tag colours stay consistent instead of being hardcoded per component.
export const colors = {
  bg: '#0f1115',
  card: '#1a1d24',
  card2: '#22262f',
  text: '#f5f6f8',
  muted: '#9aa1ad',
  accent: '#3ddc84',
  onAccent: '#08130c', // readable text on an accent-filled surface
  badge: '#e8453c',
  border: '#2a2f3a',
};

// 4-pt spacing scale (use for padding/margin/gap).
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 } as const;

// Corner radii: sm for controls, md for cards, pill for fully-rounded.
export const radius = { sm: 8, md: 12, pill: 999 } as const;

// Type scale (size + weight). `as const` keeps fontWeight a literal so it satisfies TextStyle.
export const font = {
  title: { fontSize: 22, fontWeight: '700' },
  h2: { fontSize: 18, fontWeight: '700' },
  body: { fontSize: 15, fontWeight: '500' },
  label: { fontSize: 13, fontWeight: '600' },
  small: { fontSize: 12, fontWeight: '500' },
  tiny: { fontSize: 11, fontWeight: '600' },
} as const;

// Tag/badge tints: a translucent fill + a readable foreground, one per semantic marker.
// Centralised here so OfferCard, FlyerModal, and FilterSheet share one vocabulary.
export const tint = {
  bio: { bg: 'rgba(76,175,80,0.18)', fg: '#5cc463' }, // organic green
  day: { bg: 'rgba(255,159,67,0.18)', fg: '#ff9f43' }, // day-limited orange
  app: { bg: 'rgba(255,205,0,0.16)', fg: '#ffd84d' }, // EDEKA app-price yellow
  loyalty: { bg: 'rgba(61,220,132,0.16)', fg: '#3ddc84' }, // card bonus green
  coupon: { bg: 'rgba(61,139,253,0.16)', fg: '#7da7ff' }, // Lidl Plus coupon blue
  flyer: { bg: 'rgba(240,180,60,0.16)', fg: '#e6b34d' }, // Prospekt amber
  like: { bg: 'rgba(255,107,129,0.16)', fg: '#ff6b81' }, // liked-product pink (NOT colors.badge — that red means discount/error)
  basket: { bg: 'rgba(61,220,132,0.16)', fg: '#3ddc84' }, // in-basket green (accent, translucent — matches the swipe Basket panel)
} as const;
