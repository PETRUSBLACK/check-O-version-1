"""
Notification service.
Creates a Notification record in the database AND fires a WebSocket event
to the user's channel group so they receive it in real time.

Usage:
    from apps.notifications.services.notification_service import notify

    notify(
        user=order.customer,
        title="Order Confirmed",
        body="Your order SM-1234 has been confirmed.",
        event_type="order.confirmed",
        payload={"order_id": str(order.pk)},
    )
"""

import logging

from apps.notifications.models import Notification
from realtime.websocket_utils import send_to_user

logger = logging.getLogger(__name__)


def notify(
    *,
    user,
    title: str,
    body: str = "",
    event_type: str = "notification.new",
    payload: dict = None,
) -> Notification:
    """
    Create a Notification and send it to the user via WebSocket.
    Safe to call from any service — silently logs WebSocket errors.
    """
    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        event_type=event_type,
        # Kept on the row, not only sent over the socket: the socket reaches a
        # phone that happens to be open, the row is what the inbox reads later.
        payload=payload or {},
    )

    ws_payload = {
        "notification_id": str(notification.pk),
        "event": event_type,
        "title": title,
        "body": body,
        **(payload or {}),
    }

    try:
        send_to_user(
            user_id=str(user.pk),
            event_type=event_type,
            payload=ws_payload,
        )
    except Exception:
        logger.exception(
            "websocket_send_failed user=%s event=%s notification=%s",
            user.pk, event_type, notification.pk,
        )

    return notification


# ─── Telling the shop ─────────────────────────────────────────────────────────
#
# Added 2026-10-10. Every helper below this file's original line was addressed
# to `order.customer`: order placed, payment confirmed, status changed, shipment
# moved, pickup due. Not one of them reached the person who has to pack the bag.
#
# A trader whose phone stays silent when money arrives has to keep opening
# Check-O to check, which is the behaviour an order notification exists to make
# unnecessary. It went unnoticed because the shop side of Check-O was built from
# the shopper side outwards, and because until today nothing in the app could
# display a notification at all, so nobody ever missed one.


def _shop_owner(order):
    """The person to tell, or None when there is nobody to tell."""
    business = getattr(order, "business", None)
    return getattr(business, "owner", None) if business else None


def notify_vendor_new_order(*, order) -> None:
    """
    Money has arrived and the shop has something to do.

    Deliberately sent when the order is *paid*, not when it is placed. An
    unpaid order is a 30-minute hold that may simply lapse; telling a trader to
    go and pack something that might evaporate teaches her to ignore Check-O.
    Payment is the first moment the work is real.
    """
    owner = _shop_owner(order)
    if owner is None:
        return

    count = sum(line.quantity for line in order.items.all())
    collecting = getattr(order, "fulfilment_type", "") == "pickup"

    notify(
        user=owner,
        title=f"New order — ₦{order.total:,.2f}",
        body=(
            f"{order.recipient_name or 'A customer'} paid for "
            f"{count} item{'' if count == 1 else 's'}. "
            + ("They are coming to collect it." if collecting else "It needs delivering.")
        ),
        event_type="vendor.new_order",
        payload={"order_id": str(order.pk), "total": str(order.total)},
    )


def notify_vendor_order_cancelled(*, order, by: str) -> None:
    """
    Told to the shop only when somebody else cancelled. A vendor who cancels an
    order does not need a message announcing what she just did.
    """
    if by == "vendor":
        return
    owner = _shop_owner(order)
    if owner is None:
        return

    notify(
        user=owner,
        title="An order was cancelled",
        body=(
            "The customer cancelled this order."
            if by == "customer"
            else "This order was cancelled because it was not paid in time."
        )
        + " The items have gone back on your shelf.",
        event_type="vendor.order_cancelled",
        payload={"order_id": str(order.pk), "cancelled_by": by},
    )


# ─── Typed notification helpers ───────────────────────────────────────────────

def notify_order_placed(*, order) -> None:
    notify(
        user=order.customer,
        title="Order Placed",
        body=f"Your order has been placed successfully. Total: ₦{order.total:,.2f}",
        event_type="order.placed",
        payload={"order_id": str(order.pk), "total": str(order.total)},
    )


def notify_payment_confirmed(*, order, payment) -> None:
    notify(
        user=order.customer,
        title="Payment Confirmed",
        body=f"Payment of ₦{payment.amount:,.2f} received. Your order is being prepared.",
        event_type="payment.confirmed",
        payload={"order_id": str(order.pk), "payment_id": str(payment.pk)},
    )


def notify_order_status_changed(*, order, previous_status: str) -> None:
    messages = {
        "processing": "Your order is being processed by the vendor.",
        "packaging": "Your order is being packaged.",
        "shipped": "Your order is on its way!",
        "delivered": "Your order has been delivered. Enjoy!",
        "cancelled": "Your order has been cancelled.",
        "ready_for_pickup": f"Your order is ready for pickup. Use code: {order.pickup_code}",
        "collected": "Order collected successfully. Thank you!",
        "expired": "Your pickup window expired. A full refund has been initiated.",
    }
    body = messages.get(order.status, f"Your order status is now: {order.status}")
    notify(
        user=order.customer,
        title=f"Order Update: {order.get_status_display()}",
        body=body,
        event_type="order.status_changed",
        payload={
            "order_id": str(order.pk),
            "previous_status": previous_status,
            "new_status": order.status,
        },
    )


def notify_shipment_updated(*, shipment) -> None:
    messages = {
        "processing": "Your shipment is being prepared.",
        "packaging": "Your order is being packaged for dispatch.",
        "pickup": "Your shipment is ready for pickup by the delivery agent.",
        "in_transit": "Your order is in transit and on its way to you.",
        "delivered": "Your order has been delivered!",
    }
    body = messages.get(shipment.status, f"Shipment status updated: {shipment.status}")
    notify(
        user=shipment.order.customer,
        title="Shipment Update",
        body=body,
        event_type="shipment.updated",
        payload={
            "shipment_id": str(shipment.pk),
            "order_id": str(shipment.order_id),
            "status": shipment.status,
        },
    )


def notify_pickup_reminder(*, order, hours_remaining: int) -> None:
    notify(
        user=order.customer,
        title="Pickup Reminder",
        body=f"You have {hours_remaining} hour(s) left to collect your order. Code: {order.pickup_code}",
        event_type="order.pickup_reminder",
        payload={
            "order_id": str(order.pk),
            "pickup_code": order.pickup_code,
            "hours_remaining": hours_remaining,
            "pickup_deadline": order.pickup_deadline.isoformat() if order.pickup_deadline else None,
        },
    )


def notify_pickup_expired(*, order) -> None:
    notify(
        user=order.customer,
        title="Pickup Expired — Refund Initiated",
        body="Your pickup window has expired. A full refund has been initiated and will reflect within 24-48 hours.",
        event_type="order.pickup_expired",
        payload={"order_id": str(order.pk)},
    )
