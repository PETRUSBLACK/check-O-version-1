import { api } from "../config/api";
import { CheckoutGroup } from "./cart";

export const checkoutService = {
  // GET /api/checkouts/{id}/ — one payment covering one order per shop
  async get(id: string): Promise<CheckoutGroup> {
    const { data } = await api.get<CheckoutGroup>(`/checkouts/${id}/`);
    return data;
  },
};
