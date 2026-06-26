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
  onlyOnSale: boolean; // hide recipes that need a non-staple, non-on-sale ingredient
  cheapestKg: boolean; // rank recipes by their on-sale ingredients' €/kg
};
