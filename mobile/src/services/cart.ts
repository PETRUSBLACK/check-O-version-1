import { api } from "../config/api";

export interface CartItem {
  id: string;
  product: string;
  product_name: string;
  product_price: number;
  quantity: number;
  subtotal: number;
}

export interface Cart {
  id: string;
  items: CartItem[];
  total: number;
}

export type FulfillmentMethod = "delivery" | "pickup";

export const cartService = {
  // GET /api/cart/
  async get(): Promise<Cart> {
    const { data } = await api.get("/cart/");
    return data;
  },

  // POST /api/cart/add/
  async addItem(productId: string, quantity: number): Promise<Cart> {
    const { data } = await api.post("/cart/add/", { product: productId, quantity });
    return data;
  },

  // PATCH /api/cart/update/
  async updateItem(productId: string, quantity: number): Promise<Cart> {
    const { data } = await api.patch("/cart/update/", { product: productId, quantity });
    return data;
  },

  // DELETE /api/cart/remove/{product_id}/
  async removeItem(productId: string): Promise<void> {
    await api.delete(`/cart/remove/${productId}/`);
  },

  // POST /api/cart/checkout/
  async checkout(fulfillmentMethod: FulfillmentMethod, addressId?: string) {
    const { data } = await api.post("/cart/checkout/", {
      fulfillment_method: fulfillmentMethod,
      address_id: addressId,
    });
    return data;
  },
};