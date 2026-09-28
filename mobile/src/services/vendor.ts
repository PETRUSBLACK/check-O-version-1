import { api } from "../config/api";
import { Order, OrderStatus } from "./orders";
import { Product } from "./products";

/** The shops this seller owns. */
export interface MyShop {
  id: string;
  name: string;
  slug: string;
  category: string;
  category_display: string;
  status: string;
  delivers: boolean;
  delivery_fee: string;
  address: string;
}

export const vendorService = {
  // GET /api/businesses/mine/ — this seller's shops, whatever their status
  async myShops(): Promise<MyShop[]> {
    const { data } = await api.get<MyShop[]>("/businesses/mine/");
    return data;
  },

  // GET /api/products/?business={id} — a shop's own list, including hidden ones
  async products(businessId: string): Promise<VendorProduct[]> {
    const { data } = await api.get<{ results: VendorProduct[] } | VendorProduct[]>("/products/", {
      params: { business: businessId },
    });
    return Array.isArray(data) ? data : data.results;
  },

  // GET /api/products/{id}/ — the owner's view, with real stock and allocation
  async product(id: string): Promise<VendorProduct> {
    const { data } = await api.get<VendorProduct>(`/products/${id}/`);
    return data;
  },

  // PATCH /api/products/{id}/
  async updateProduct(id: string, changes: ProductChanges): Promise<VendorProduct> {
    const { data } = await api.patch<VendorProduct>(`/products/${id}/`, changes);
    return data;
  },

  // POST /api/products/
  async addProduct(input: ProductChanges & { business: string; name: string }): Promise<VendorProduct> {
    const { data } = await api.post<VendorProduct>("/products/", input);
    return data;
  },

  // POST /api/orders/{id}/transition/
  async advance(id: string, status: OrderStatus): Promise<Order> {
    const { data } = await api.post<Order>(`/orders/${id}/transition/`, { status });
    return data;
  },

  // POST /api/orders/{id}/ready-for-pickup/
  async markReady(id: string): Promise<Order> {
    const { data } = await api.post<Order>(`/orders/${id}/ready-for-pickup/`, {});
    return data;
  },

  // POST /api/orders/{id}/confirm-pickup/
  async confirmCollected(id: string, pickupCode: string): Promise<Order> {
    const { data } = await api.post<Order>(`/orders/${id}/confirm-pickup/`, {
      pickup_code: pickupCode.trim().toUpperCase(),
    });
    return data;
  },

  // POST /api/orders/{id}/cancel/ — a shop must say why
  async cancel(id: string, reason: VendorCancelReason, note = ""): Promise<Order> {
    const { data } = await api.post<Order>(`/orders/${id}/cancel/`, { reason, note });
    return data;
  },
};

export type VendorCancelReason = "out_of_stock" | "item_damaged" | "other";

export const CANCEL_REASONS: { value: VendorCancelReason; label: string }[] = [
  { value: "out_of_stock", label: "I don't have it in stock" },
  { value: "item_damaged", label: "The item is damaged" },
  { value: "other", label: "Another reason" },
];

/**
 * The single next thing this shop should do with an order, in their words.
 * Returns null when the order needs nothing from them.
 */
export function nextAction(order: Order): {
  label: string;
  run: "processing" | "packaging" | "shipped" | "delivered" | "ready" | "collected";
  hint: string;
} | null {
  const collecting = order.fulfilment_type === "pickup";
  switch (order.status) {
    case "paid":
      return collecting
        ? { label: "Start preparing", run: "processing", hint: "The customer is waiting." }
        : { label: "Start preparing", run: "processing", hint: "The customer is waiting." };
    case "processing":
      return collecting
        ? { label: "Ready to collect", run: "ready", hint: "This gives the customer a code." }
        : { label: "Packed and ready", run: "packaging", hint: "" };
    case "packaging":
      return collecting
        ? { label: "Ready to collect", run: "ready", hint: "This gives the customer a code." }
        : { label: "Sent out for delivery", run: "shipped", hint: "" };
    case "shipped":
      return { label: "Delivered", run: "delivered", hint: "Only once it has reached them." };
    case "ready_for_pickup":
      return {
        label: "Customer collected it",
        run: "collected",
        hint: "Ask for their code first.",
      };
    default:
      return null;
  }
}

/** A shop may cancel until the goods leave it. */
export function vendorCanCancel(order: Order): boolean {
  return ["pending_payment", "paid", "processing", "packaging", "ready_for_pickup"].includes(
    order.status,
  );
}

/** Orders that still need the shop to do something. */
export function needsAction(order: Order): boolean {
  return ["paid", "processing", "packaging", "shipped", "ready_for_pickup"].includes(order.status);
}


/**
 * The shop's own view of a product. Unlike a shopper, the owner sees the real
 * stock count and what they've set aside for Check-O.
 */
export interface VendorProduct extends Product {
  stock: number;
  smartmall_allocation: number | null;
  cost_price: string | null;
  low_stock_threshold: number;
}

export interface ProductChanges {
  name?: string;
  description?: string;
  price?: string;
  stock?: number;
  /** null means Check-O may sell everything in the shop. */
  smartmall_allocation?: number | null;
  is_active?: boolean;
}

/** What the shop should understand about a product at a glance. */
export function shelfNote(product: VendorProduct): { text: string; tone: "ok" | "low" | "out" | "hidden" } {
  if (!product.is_active) return { text: "Not on Check-O", tone: "hidden" };
  if (product.available_stock <= 0) return { text: "Sold out", tone: "out" };
  if (product.available_stock <= 5) return { text: `Only ${product.available_stock} left`, tone: "low" };
  return { text: `${product.available_stock} available`, tone: "ok" };
}
