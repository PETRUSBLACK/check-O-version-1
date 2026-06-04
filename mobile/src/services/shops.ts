import { api } from "../config/api";

// ─── Types — mirror backend Business model ────────────────────────────────────

export interface Shop {
  id: string;
  name: string;
  slug: string;
  status: "draft" | "pending" | "approved" | "rejected";
  address: string;
  business_phone: string;
  average_rating: number;
  rating_count: number;
  // Location fields (set via POST /businesses/{id}/location/)
  latitude?: number;
  longitude?: number;
  distance_km?: number;     // present on /shops/nearby/ results
  walk_minutes?: number;    // present on /shops/nearby/ results
  categories?: string[];
  is_open?: boolean;
}

export interface NearbyShopsParams {
  lat: number;
  lng: number;
  radius_km?: number;       // default 5 on backend
  category?: string;
}

// ─── Shops service ────────────────────────────────────────────────────────────

export const shopsService = {
  // GET /api/shops/nearby/ — home screen "Shops near you"
  async getNearby(params: NearbyShopsParams): Promise<Shop[]> {
    const { data } = await api.get("/shops/nearby/", { params });
    return data.results ?? data;
  },

  // GET /api/businesses/ — full list (approved only for customers)
  async list(): Promise<Shop[]> {
    const { data } = await api.get("/businesses/");
    return data.results ?? data;
  },

  // GET /api/businesses/{id}/
  async get(id: string): Promise<Shop> {
    const { data } = await api.get(`/businesses/${id}/`);
    return data;
  },

  // GET /api/businesses/{id}/ratings/
  async getRatings(id: string) {
    const { data } = await api.get(`/businesses/${id}/ratings/`);
    return data.results ?? data;
  },

  // POST /api/businesses/{id}/rate/
  async rate(id: string, rating: number, comment?: string) {
    const { data } = await api.post(`/businesses/${id}/rate/`, {
      rating,
      comment,
    });
    return data;
  },
};