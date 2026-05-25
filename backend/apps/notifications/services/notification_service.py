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
