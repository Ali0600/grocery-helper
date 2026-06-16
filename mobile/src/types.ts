export type Offer = {
  id: number;
  store_id: number;
  chain: string;
  store_name: string;
  name: string;
  brand: string | null;
  category: string;
  category_label: string;
  price_cents: number;
  regular_price_cents: number | null;
  discount_pct: number | null;
  unit: string | null;
  image_url: string | null;
  valid_from: string | null;
  valid_to: string | null;
};

export type CategoryCount = {
  category: string;
  label: string;
  count: number;
};
