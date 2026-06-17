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
  price_cents: number;
  regular_price_cents: number | null;
  discount_pct: number | null;
  unit: string | null;
  price_per_unit: string | null; // "1 kg = 13.33" (formatted client-side)
  loyalty_note: string | null; // REWE card bonus, e.g. "1,00 € Bonus"
  image_url: string | null;
  valid_from: string | null;
  valid_to: string | null;
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

// A store the user saved to "My stores" (persisted locally; address-only for now).
export type MyStore = {
  chain: string;
  label: string;
  name: string;
  address: string | null;
};

export type ScrapeResult = {
  plz: string;
  scraped: number;
  stores: Store[];
};
