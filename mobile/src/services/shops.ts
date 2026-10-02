import { api } from "../config/api";

// Mirrors GET /api/shops/nearby/ (apps/businesses/views/location_views.py)
export interface NearbyShop {
  business_id: string;
  name: string;
  category: string;
  category_display: string;
  address: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  avg_rating: number | null;
  rating_count: number;
}

export interface NearbyParams {
  lat: number;
  lng: number;
  radius_km?: number;
  category?: string;
  product?: string;
}

// Backend BusinessCategory values used by the Home screen tiles
export type ShopCategory =
  | "supermarket"
  | "pharmacy"
  | "restaurant"
  | "fashion"
  | "beauty"
  | "electronics"
  | "health"
  | "retail";

// Mirrors GET /api/businesses/{id}/ (BusinessDetailSerializer) — the fields the app uses.
export interface ShopDetail {
  id: string;
  name: string;
  slug: string;
  category: string;
  category_display: string;
  avg_rating: number | null;
  rating_count: number;
  tagline: string;
  description: string;
  logo: string | null;
  cover_image: string | null;
  business_phone: string;
  /** What the vendor typed on the business form. Often blank — prefer display_address. */
  address: string;
  /**
   * The address to actually show a customer. The backend picks between the two it
   * holds: the shop's location (the one tied to the GPS used for distance) if set,
   * otherwise the business form's address. Empty string when neither is filled.
   */
  display_address: string;
}

export const shopsService = {
  async get(id: string): Promise<ShopDetail> {
    const { data } = await api.get<ShopDetail>(`/businesses/${id}/`);
    return data;
  },

  async nearby(params: NearbyParams): Promise<NearbyShop[]> {
    const { data } = await api.get<NearbyShop[]>("/shops/nearby/", {
      params: { radius_km: 15, ...params },
    });
    return data;
  },
};
