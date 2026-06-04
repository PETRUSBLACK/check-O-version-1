import { api } from "../config/api";

export interface Order {
  id: string;
  status: "pending" | "confirmed" | "paid" | "processing" | "shipped" | "delivered" | "completed" | "cancelled";
  fulfillment_method: "delivery" | "pickup";
  pickup_code?: string;
  total: number;
  created_at: string;
  items: {
    product_name: string;
    quantity: number;
    unit_price: number;
    subtotal: number;
  }[];
}

export const ordersService = {
  // GET /api/orders/
  async list(): Promise<Order[]> {
    const { data } = await api.get("/orders/");
    return data.results ?? data;
  },

  // GET /api/orders/{id}/
  async get(id: string): Promise<Order> {
    const { data } = await api.get(`/orders/${id}/`);
    return data;
  },
};