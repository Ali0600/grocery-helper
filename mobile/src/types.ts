export type Offer = {
  id: number;
  store_id: number;
  chain: string;
  store_name: string;
  source: 'coupon' | 'flyer';
  name: string;
  brand: string | null;
  category: string;
  category_label: string;
  group: string | null; // product sub-group key within the category, e.g. "avocado"
  group_label: string | null; // its display label, e.g. "Avocado"
  price_cents: number;
  regular_price_cents: number | null;
  discount_pct: number | null;
  unit: string | null;
  price_per_unit: string | null; // "1 kg = 13.33" (formatted client-side)
  unit_price_cents: number | null; // normalized cents per kg/l, for the €/kg sort
  loyalty_note: string | null; // REWE card bonus, e.g. "1,00 € Bonus"
  app_price_cents: number | null; // EDEKA app-coupon price (below price_cents)
  image_url: string | null;
  valid_from: string | null;
  valid_to: string | null;
  valid_days: string | null; // day-limited label, e.g. "Do–Sa" / "Fr"; null = valid all week
  day_limited: boolean; // valid fewer than the normal Mon–Sat week
  is_bio: boolean; // organic ("Bio") product, detected from the name/brand server-side
};

export type CategoryCount = {
  category: string;
  label: string;
  count: number;
};

export type Store = {
  id: number;
  chain: string;
  name: string;
  plz: string;
  market_code: string | null;
};

// A nearby store of a known chain, from /api/nearby-stores (OSM).
export type NearbyStore = {
  chain: string;
  label: string;
  name: string;
  address: string | null;
  lat: number;
  lng: number;
  distance_m: number;
  active: boolean; // chains we already scrape deals for (lidl/rewe)
};

// A store the user saved to "My stores" (persisted locally; one per chain — the
// specific branch they picked). Coords are kept for a future directions link.
export type MyStore = {
  chain: string;
  label: string;
  name: string;
  address: string | null;
  lat?: number;
  lng?: number;
};

// An item on the user's basket / shopping list (persisted locally). Only the wishlist
// persists; the matched deals are recomputed each session (offer ids churn weekly).
// `keywords` are German name-stems matched against offer names; `exclude` guards the
// substring traps (e.g. leek must not match "Knoblauch"). Catalog adds carry the
// curated lists; a free-text add gets a single normalized keyword and no exclude.
export type BasketItem = {
  key: string; // stable id (catalog key, or "free:<normalized text>")
  label: string; // display label (English chrome, e.g. "Strawberry"; or the typed text)
  keywords: string[];
  exclude?: string[];
};

// A product recorded in History when you added it to your basket (persisted locally).
// Persists the product's IDENTITY, never offer.id (ids churn weekly); the History page
// re-matches it against the loaded offers each session — exact name first, else brand (else
// sub-group) fallback, see history.ts. `chain`/`addedPriceCents`/`addedAt` are display-only
// memos of the moment you added it ("what you paid"); matching is cross-chain.
export type HistoryItem = {
  key: string; // normName(name) — stable identity + dedupe key
  name: string; // as displayed when added ("McCain Golden Longs")
  brand: string | null; // fallback tier ("McCain")
  group: string | null; // fallback tier for brandless items ("tomate")
  groupLabel: string | null;
  chain: string;
  addedPriceCents: number;
  addedAt: number;
};

export type ScrapeResult = {
  plz: string;
  scraped: number;
  stores: Store[];
};

// POST /api/reset — wiped the backend DB, then re-scraped. `deleted` = rows removed.
export type ResetResult = {
  plz: string;
  deleted: number;
  scraped: number;
  stores: Store[];
};

// GET /api/offers/{id}/payload — the full raw source object the offer was scraped from
// (flyer `content` dict / Lidl coupon dict). `payload` is null if it wasn't captured
// (offer scraped before the field existed, or sample-data fallback).
export type OfferPayload = {
  id: number;
  source: string;
  payload: Record<string, unknown> | null;
};

// GET /api/offers/payloads?plz= — every offer's raw payload for a PLZ, keyed by offer id
// (string). Prefetched + cached on-device so "View payload" is instant + offline. A value
// is null where the payload wasn't captured (like OfferPayload.payload).
export type PayloadMap = Record<string, Record<string, unknown> | null>;

// --- "Why this category?" — the classifier's per-layer trace (GET .../category-trace) ---
// Which rule decided the category, which layers were skipped and why, and what the LOSING
// layers would have said. Most fields are absent rather than null: the bulk form drops
// everything derivable to keep the prefetch ~1.3 MB, so treat them all as optional and
// render layer names from LAYER_LABELS (mobile/src/categoryTrace.ts), never from the wire.
export type TraceLayer = {
  layer: string; // "0" | "1" | "2" | "2b" | "3" | "4" | "5" | "6" | "7"
  status: 'decided' | 'skipped' | 'no_match';
  slug?: string; // what it decided — or WOULD have, when it isn't the winner
  table?: string; // the rule table that matched, e.g. "_FORM_OVERRIDES"
  index?: number; // position in it — slugs repeat, so this is what names the rule
  matched?: string; // the exact token / brand key / path node
  where?: string; // which haystack matched (only meaningful on a decided layer)
  reason?: string; // why it was skipped, or which branch of layer 1 ran
  blocked_slug?: string; // layer 1: the rescue a veto word killed
};

export type CategoryTrace = {
  category: string;
  inputs: {
    category_path?: string[]; // the source taxonomy path — NOT exposed on Offer
    name?: string;
    brand?: string | null;
    unit?: string | null;
    text?: string; // the real space-padded haystack (per-offer endpoint only)
    caption?: string;
  };
  layers: TraceLayer[];
};

export type OfferCategoryTrace = {
  id: number;
  stored_category: string;
  stored_label: string;
  computed_category: string;
  computed_label: string;
  stale: boolean; // stored category predates a rules change -> prod needs a re-scrape
  trace: CategoryTrace;
};

// GET /api/offers/category-traces?plz= — every offer's trace, keyed by offer id (string).
export type TraceMap = Record<string, OfferCategoryTrace>;

// --- AI Recipes (offline-authored, bundled in the app; no runtime API) ---

// One ingredient line in a recipe. `keywords`/`exclude` are German name stems matched
// against the user's loaded offers (same signal as the Basket), so the app can show the
// live on-sale price. `staple` marks a pantry item assumed on hand (oil, salt) — never "buy".
export type RecipeIngredient = {
  label: string; // display, e.g. "Chicken breast"
  keywords: string[]; // German stems matched as substrings of offer names
  qty?: string; // optional amount, e.g. "400 g", "2"
  staple?: boolean; // pantry assumed on hand — never counted as "buy"
  exclude?: string[]; // substring-trap guards (e.g. tomato vs "ketchup")
};

export type Recipe = {
  id: string;
  title: string;
  summary: string;
  servings: number;
  timeMinutes: number;
  tags: string[]; // dietary + cuisine + meal, e.g. ["vegetarian", "italian", "dinner"]
  ingredients: RecipeIngredient[];
  steps: string[];
};

// The bundled data file the offline authoring step rewrites each week.
export type RecipesData = {
  generatedFor: string; // PLZ the deals snapshot came from
  generatedAt: string; // ISO date the recipes were authored
  recipes: Recipe[];
};

// Persisted recipe filters (session prefs).
export type RecipePrefs = {
  servings: number; // scales the displayed quantities
  count: number; // how many recipes to show
  diet: string | null; // "vegetarian" | "vegan" | "gluten-free" | "no-pork" | null
  cuisine: string | null; // "italian" | "asian" | "german" | ... | null
  stores: string[]; // chains to shop at; EMPTY = any store. Capped at MAX_RECIPE_STORES.
  onlyOnSale: boolean; // hide recipes that need a non-staple, non-on-sale ingredient
  cheapestKg: boolean; // rank recipes by their on-sale ingredients' €/kg
};
