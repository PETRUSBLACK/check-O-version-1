import { api } from "../config/api";

/**
 * The inbox.
 *
 * This file should have existed in September. Check-O has been writing
 * notifications to the database since then — order placed, payment confirmed,
 * shop approved, stock running low — and until today nothing in the app could
 * read a single one of them. Petrus approved his own shop on 10 October, was
 * told nothing, and went looking in the Django admin to find the message
 * sitting there unread.
 */

/** The kinds the backend sends. Anything unrecognised still displays fine. */
export type NotificationEvent =
  | "notification.new"
  | "order.placed"
  | "order.status_changed"
  | "order.pickup_reminder"
  | "order.pickup_expired"
  | "order.refund_due"
  | "payment.confirmed"
  | "shipment.updated"
  | "business.submitted"
  | "business.approved"
  | "business.rejected"
  | "inventory.low_stock"
  | "vendor.new_order"
  | "vendor.order_cancelled";

/** Mirrors apps/notifications NotificationSerializer. */
export interface Notification {
  id: string;
  title: string;
  body: string;
  event_type: NotificationEvent | string;
  /** Whichever ids the event refers to — see `destinationOf`. */
  payload: Record<string, unknown>;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  updated_at: string;
}

interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const notificationsService = {
  // GET /api/notifications/
  async list(): Promise<Notification[]> {
    const { data } = await api.get<Page<Notification> | Notification[]>("/notifications/");
    return Array.isArray(data) ? data : data.results;
  },

  // GET /api/notifications/unread-count/
  async unreadCount(): Promise<number> {
    const { data } = await api.get<{ unread: number }>("/notifications/unread-count/");
    return data.unread;
  },

  // POST /api/notifications/{id}/read/
  async markRead(id: string): Promise<Notification> {
    const { data } = await api.post<Notification>(`/notifications/${id}/read/`, {});
    return data;
  },

  // POST /api/notifications/read-all/
  async markAllRead(): Promise<number> {
    const { data } = await api.post<{ marked: number }>("/notifications/read-all/", {});
    return data.marked;
  },
};

// ─── Reading a notification ───────────────────────────────────────────────────

function id(payload: Record<string, unknown>, key: string): string | null {
  const value = payload?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

export interface Destination {
  href: string;
  /**
   * True when the destination is one of the tabs the inbox was opened from.
   *
   * This distinction is not fussiness, it is a bug that reached a real person.
   * The inbox is pushed *on top of* the tabs, so navigating to one of them
   * switches the tab underneath while the inbox stays where it is. The app
   * obeys perfectly and the vendor sees absolutely nothing happen. Petrus hit
   * this on 2026-10-10, tapping "Shop O is open on Check-O" over and over.
   *
   * A destination marked this way has to have the inbox closed first.
   */
  inTabsBelow: boolean;
}

/**
 * Where tapping a notification should take you, or null when there is nowhere
 * useful to go.
 *
 * Returning null is a real answer, not a failure: "A shop is waiting for
 * review" goes to Check-O's reviewers, who do that work in the Django admin, so
 * the message is worth reading and there is no screen behind it. A row that
 * doesn't navigate is better than one that navigates somewhere wrong.
 */
export function destinationOf(n: Notification): Destination | null {
  const orderId = id(n.payload, "order_id");
  const businessId = id(n.payload, "business_id");

  const screen = (href: string): Destination => ({ href, inTabsBelow: false });
  const tab = (href: string): Destination => ({ href, inTabsBelow: true });

  switch (n.event_type) {
    case "order.placed":
    case "order.status_changed":
    case "order.pickup_reminder":
    case "order.pickup_expired":
    case "order.refund_due":
    case "payment.confirmed":
    case "shipment.updated":
      return orderId ? screen(`/order/${orderId}`) : tab("/orders");

    // The shop's own orders, which are a different screen from the shopper's
    // view of the same order — one has a "mark as ready" button on it.
    case "vendor.new_order":
    case "vendor.order_cancelled":
      return orderId ? screen(`/vendor-order/${orderId}`) : tab("/(vendor)");

    case "inventory.low_stock":
      // The owner's own shelf, not a shopper's view of the shop.
      return tab("/(vendor)/products");

    case "business.approved":
    case "business.rejected":
      return tab("/(vendor)/shop");

    case "business.submitted":
      // Reviewers only. Nothing in the app approves shops yet.
      return null;

    default:
      // An event this build has not heard of — if it names an order or a shop,
      // that is still a good guess; otherwise just let it be read.
      if (orderId) return screen(`/order/${orderId}`);
      if (businessId) return screen(`/shop/${businessId}`);
      return null;
  }
}

/** The icon that goes with a notification, so the list can be scanned. */
export function iconOf(n: Notification): "package" | "credit-card" | "truck" | "home" | "alert-triangle" | "bell" {
  if (n.event_type.startsWith("payment.")) return "credit-card";
  if (n.event_type === "shipment.updated") return "truck";
  if (n.event_type.startsWith("order.") || n.event_type.startsWith("vendor.")) return "package";
  if (n.event_type === "inventory.low_stock") return "alert-triangle";
  if (n.event_type.startsWith("business.")) return "home";
  return "bell";
}

/**
 * "4 minutes ago", "Yesterday", "10 Oct". Short, because it sits beside the
 * title and the title is the part that matters.
 */
export function whenOf(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return "";

  const seconds = Math.floor((Date.now() - then.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;

  return then.toLocaleDateString("en-NG", {
    day: "numeric",
    month: "short",
    ...(then.getFullYear() === new Date().getFullYear() ? {} : { year: "numeric" }),
  });
}
