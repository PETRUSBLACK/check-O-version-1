import { api } from "../config/api";

export type OrderStatus =
  | "draft"
  | "pending_payment"
  | "paid"
  | "processing"
  | "packaging"
  | "shipped"
  | "delivered"
  | "ready_for_pickup"
  | "collected"
  | "cancelled"
  | "expired";

export interface OrderItem {
  id: string;
  product: string;
  product_name: string;
  quantity: number;
  unit_price: string;
}

/** Mirrors apps/orders OrderSerializer. */
export interface Order {
  id: string;
  customer: string;
  business: string | null;
  business_name: string | null;
  checkout_group: string | null;
  status: OrderStatus;
  items_total: string;
  delivery_fee: string;
  total: string;
  items: OrderItem[];
  fulfilment_type: "delivery" | "pickup";
  delivery_address: string;
  recipient_name: string;
  delivery_phone: string;
  pickup_code: string;
  pickup_deadline: string | null;
  paid_at: string | null;
  cancelled_at: string | null;
  cancelled_by: string;
  cancellation_reason: string;
  cancellation_note: string;
  refund_status: string;
  created_at: string;
}

interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const ordersService = {
  // GET /api/orders/
  async list(): Promise<Order[]> {
    const { data } = await api.get<Page<Order> | Order[]>("/orders/");
    return Array.isArray(data) ? data : data.results;
  },

  // GET /api/orders/{id}/
  async get(id: string): Promise<Order> {
    const { data } = await api.get<Order>(`/orders/${id}/`);
    return data;
  },

  // POST /api/orders/{id}/cancel/
  async cancel(id: string): Promise<Order> {
    const { data } = await api.post<Order>(`/orders/${id}/cancel/`, {});
    return data;
  },
};

/**
 * What the shopper should understand by each status — their words, not the
 * database's. The second line is what happens next, where that isn't obvious.
 */
export function statusLook(order: Order): {
  label: string;
  detail: string;
  tone: "waiting" | "active" | "done" | "bad";
} {
  const collecting = order.fulfilment_type === "pickup";
  switch (order.status) {
    case "pending_payment":
      return {
        label: "Waiting for payment",
        detail: "Held for 30 minutes from when you ordered.",
        tone: "waiting",
      };
    case "paid":
      return { label: "Paid", detail: "Waiting for the shop to start on it.", tone: "active" };
    case "processing":
      return { label: "Being prepared", detail: "The shop is putting it together.", tone: "active" };
    case "packaging":
      return { label: "Being packed", detail: "Almost ready.", tone: "active" };
    case "ready_for_pickup":
      return {
        label: "Ready to collect",
        detail: "Show your code at the shop.",
        tone: "active",
      };
    case "shipped":
      return { label: "On the way", detail: "Out for delivery.", tone: "active" };
    case "delivered":
      return { label: "Delivered", detail: "", tone: "done" };
    case "collected":
      return { label: "Collected", detail: "", tone: "done" };
    case "cancelled":
      return { label: "Cancelled", detail: cancelledBy(order), tone: "bad" };
    case "expired":
      return {
        label: collecting ? "Not collected in time" : "Expired",
        detail: "The items went back to the shop.",
        tone: "bad",
      };
    default:
      return { label: "Draft", detail: "", tone: "waiting" };
  }
}

function cancelledBy(order: Order): string {
  const reason =
    order.cancellation_reason === "out_of_stock"
      ? "the item was out of stock"
      : order.cancellation_reason === "item_damaged"
        ? "the item was damaged"
        : order.cancellation_note || "";
  if (order.cancelled_by === "vendor") {
    return reason ? `The shop cancelled: ${reason}.` : "The shop cancelled this order.";
  }
  if (order.cancelled_by === "system") {
    return "Cancelled automatically because it wasn't paid in time.";
  }
  if (order.cancelled_by === "customer") return "You cancelled this order.";
  return reason;
}

/** The customer may cancel until the shop starts preparing the order. */
export function canCancel(order: Order): boolean {
  return order.status === "pending_payment" || order.status === "paid";
}

export function refundNote(order: Order): string | null {
  if (order.refund_status === "due") return "Your refund is being processed.";
  if (order.refund_status === "done") return "This order has been refunded.";
  return null;
}
