import { api } from "../config/api";
import { Product } from "./products";

// Mirrors apps/cart CartSerializer.
export interface CartItem {
  id: string;
  product: Product;
  quantity: number;
  line_total: string;
}

export interface Cart {
  id: string;
  items: CartItem[];
  total: string;
  item_count: number;
}

export const cartService = {
  // GET /api/cart/
  async get(): Promise<Cart> {
    const { data } = await api.get<Cart>("/cart/");
    return data;
  },

  // POST /api/cart/add/  — adds to whatever is already in the cart
  async add(productId: string, quantity = 1): Promise<Cart> {
    const { data } = await api.post<Cart>("/cart/add/", { product_id: productId, quantity });
    return data;
  },

  // PATCH /api/cart/update/  — sets an exact quantity; 0 removes the line
  async setQuantity(productId: string, quantity: number): Promise<Cart> {
    const { data } = await api.patch<Cart>("/cart/update/", { product_id: productId, quantity });
    return data;
  },

  // DELETE /api/cart/remove/{product_id}/
  async remove(productId: string): Promise<Cart> {
    const { data } = await api.delete<Cart>(`/cart/remove/${productId}/`);
    return data;
  },
};

/**
 * How many things are in the cart. The API's item_count is the number of lines,
 * but a shopper counts units: 12 bags of rice and 1 pack of tablets is 13 items.
 */
export function unitCount(cart: Cart): number {
  return cart.items.reduce((total, item) => total + item.quantity, 0);
}

/** The cart can hold items from several shops; checkout makes one order per shop. */
export interface ShopGroup {
  businessId: string;
  businessName: string;
  items: CartItem[];
  total: number;
}

export function groupByShop(cart: Cart): ShopGroup[] {
  const groups = new Map<string, ShopGroup>();
  for (const item of cart.items) {
    const id = item.product.business;
    let group = groups.get(id);
    if (!group) {
      group = { businessId: id, businessName: item.product.business_name, items: [], total: 0 };
      groups.set(id, group);
    }
    group.items.push(item);
    group.total += Number(item.line_total);
  }
  return [...groups.values()];
}
