import logging
from decimal import Decimal
from typing import Iterable, Optional
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.orders.models import (
    CancellationReason,
    CancelledBy,
    FulfilmentType,
    Order,
    OrderItem,
    OrderStatus,
    RefundStatus,
    StockReservation,
)
from apps.orders.services.stock_service import (
    confirm_order_stock,
    release_order_stock,
    reserve_stock,
)
from apps.products.models import Product

logger = logging.getLogger(__name__)


class OrderFlowError(Exception):
    pass


class OrderPermissionError(OrderFlowError):
    """The user is not allowed to perform this action on the order."""
    pass


_ALLOWED_TRANSITIONS = {
    OrderStatus.DRAFT.value: {OrderStatus.PENDING_PAYMENT.value, OrderStatus.CANCELLED.value},
    OrderStatus.PENDING_PAYMENT.value: {OrderStatus.PAID.value, OrderStatus.CANCELLED.value},
    OrderStatus.PAID.value: {OrderStatus.PROCESSING.value, OrderStatus.CANCELLED.value, OrderStatus.READY_FOR_PICKUP.value},
    OrderStatus.PROCESSING.value: {OrderStatus.PACKAGING.value, OrderStatus.CANCELLED.value},
    OrderStatus.PACKAGING.value: {OrderStatus.SHIPPED.value, OrderStatus.READY_FOR_PICKUP.value},
    OrderStatus.SHIPPED.value: {OrderStatus.DELIVERED.value},
    OrderStatus.DELIVERED.value: set(),
    OrderStatus.CANCELLED.value: set(),
    OrderStatus.READY_FOR_PICKUP.value: {OrderStatus.COLLECTED.value, OrderStatus.EXPIRED.value},
    OrderStatus.COLLECTED.value: set(),
    OrderStatus.EXPIRED.value: set(),
}


def _lines_from_payload(lines: Iterable[dict]) -> list[tuple[UUID, int]]:
    return [(UUID(str(row["product_id"])), int(row["quantity"])) for row in lines]


@transaction.atomic
def create_order_with_lines(*, customer, lines: Iterable[dict]) -> Order:
    parsed = _lines_from_payload(lines)
    order = Order.objects.create(
        customer=customer,
        status=OrderStatus.PENDING_PAYMENT,
        total=Decimal("0.00"),
    )
    total = Decimal("0.00")
    for product_id, qty in parsed:
        product = Product.objects.select_for_update().select_related("business").get(pk=product_id)
        if not product.is_active or product.business.status != "approved":
            raise OrderFlowError("Product not available")
        # One order = one shop. Multi-shop purchases go through cart checkout.
        if order.business_id is None:
            order.business_id = product.business_id
        elif order.business_id != product.business_id:
            raise OrderFlowError(
                "All items in an order must come from the same shop. "
                "Use the cart to buy from several shops at once."
            )
        if product.available_stock < qty:
            raise OrderFlowError("Insufficient stock")
        line_total = product.price * qty
        OrderItem.objects.create(order=order, product=product, quantity=qty, unit_price=product.price)
        total += line_total
        reserve_stock(order=order, product=product, quantity=qty)
    order.total = total
    order.save(update_fields=["total", "business", "updated_at"])
    return order


@transaction.atomic
def transition_order_status(*, order_id: UUID, to_status: str) -> Order:
    order = Order.objects.select_for_update().get(pk=order_id)
    valid = {c.value for c in OrderStatus}
    if to_status not in valid:
        raise OrderFlowError("Invalid status")
    if order.status == to_status:
        return order
    allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
    if to_status not in allowed:
        raise OrderFlowError(f"Invalid status transition from {order.status} to {to_status}")

    if to_status == OrderStatus.CANCELLED.value:
        # All cancellations release stock and flag refunds the same way
        return _apply_cancellation(
            order=order,
            by=CancelledBy.SYSTEM,
            user=None,
            reason=CancellationReason.OTHER,
        )

    previous_status = order.status
    order.status = to_status

    # Handle pickup-specific logic
    if to_status == OrderStatus.READY_FOR_PICKUP.value:
        order.generate_pickup_code()
        order.set_pickup_deadline(hours=48)

    order.save(update_fields=["status", "pickup_code", "pickup_deadline", "updated_at"])

    # Fire notification
    try:
        from apps.notifications.services.notification_service import notify_order_status_changed
        notify_order_status_changed(order=order, previous_status=previous_status)
    except Exception:
        pass

    return order


@transaction.atomic
def expire_pickup_order(*, order_id: UUID) -> Order:
    """
    Called by the background task when a pickup order window expires.
    Cancels the order and triggers a refund.
    """
    order = Order.objects.select_for_update().select_related("customer").get(pk=order_id)

    if order.status != OrderStatus.READY_FOR_PICKUP.value:
        return order

    order.status = OrderStatus.EXPIRED.value
    order.save(update_fields=["status", "updated_at"])

    # Return stock to the bucket it came from (allocation or main stock)
    release_order_stock(order=order)

    # Flag refund
    _initiate_refund_for_expired_order(order=order)

    # Notify customer
    try:
        from apps.notifications.services.notification_service import notify_pickup_expired
        notify_pickup_expired(order=order)
    except Exception:
        pass

    return order


def _initiate_refund_for_expired_order(*, order: Order) -> None:
    """Flag the order for a manual refund if it was paid."""
    if _has_successful_payment(order):
        order.refund_status = RefundStatus.DUE
        order.save(update_fields=["refund_status", "updated_at"])
        logger.info("refund_due order=%s reason=pickup_expired", order.pk)


# ─── Payment ──────────────────────────────────────────────────────────────────

def _has_successful_payment(order: Order) -> bool:
    """True if this order was paid, directly or as part of a checkout group."""
    from django.db.models import Q
    from apps.payments.models import Payment, PaymentStatus
    covers_order = Q(order=order)
    if order.checkout_group_id:
        covers_order |= Q(checkout_group_id=order.checkout_group_id)
    return Payment.objects.filter(covers_order, status=PaymentStatus.SUCCESS).exists()


@transaction.atomic
def mark_order_paid(*, order_id: UUID, payment_started_at=None) -> Order:
    """
    Called once a payment has been confirmed by the gateway.
    - Normal case: order becomes PAID and its held stock is confirmed as sold.
    - Payment arrived after the order was already cancelled (e.g. paid after the
      30-minute window and the stock was released): flag the order for a refund.
    - `payment_started_at`: for a checkout paid in one go, an order the customer
      cancelled BEFORE starting the payment was not included in the amount, so
      it is left alone.
    """
    order = Order.objects.select_for_update().get(pk=order_id)

    if (
        order.status == OrderStatus.CANCELLED.value
        and payment_started_at is not None
        and order.cancelled_at is not None
        and order.cancelled_at < payment_started_at
    ):
        return order

    if order.status == OrderStatus.PENDING_PAYMENT.value:
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)
        order.refresh_from_db()
        order.paid_at = timezone.now()
        order.save(update_fields=["paid_at", "updated_at"])
        confirm_order_stock(order=order)
    elif order.status == OrderStatus.CANCELLED.value:
        order.refund_status = RefundStatus.DUE
        order.save(update_fields=["refund_status", "updated_at"])
        logger.warning("payment_after_cancellation order=%s refund_due", order.pk)
        try:
            from apps.notifications.services.notification_service import notify
            notify(
                user=order.customer,
                title="Payment received after order was cancelled",
                body=(
                    "Your payment arrived after this order had been cancelled. "
                    "You will be refunded in full."
                ),
                event_type="order.refund_due",
                payload={"order_id": str(order.pk)},
            )
        except Exception:
            logger.exception("notify_refund_due_failed order=%s", order.pk)
    return order


# ─── Cancellation ─────────────────────────────────────────────────────────────

# Customer may cancel until the shop starts working on the order.
_CUSTOMER_CANCELLABLE = {
    OrderStatus.PENDING_PAYMENT.value,
    OrderStatus.PAID.value,
}
# Vendor / admin may cancel at any point before the goods leave the shop.
_VENDOR_CANCELLABLE = {
    OrderStatus.PENDING_PAYMENT.value,
    OrderStatus.PAID.value,
    OrderStatus.PROCESSING.value,
    OrderStatus.PACKAGING.value,
    OrderStatus.READY_FOR_PICKUP.value,
}
_VENDOR_REASONS = {
    CancellationReason.OUT_OF_STOCK.value,
    CancellationReason.ITEM_DAMAGED.value,
    CancellationReason.OTHER.value,
}


def _cancel_role(user, order: Order) -> Optional[str]:
    if user.is_staff or getattr(user, "role", None) == "admin":
        return CancelledBy.ADMIN
    if order.customer_id == user.id:
        return CancelledBy.CUSTOMER
    if getattr(user, "role", None) == "vendor" and OrderItem.objects.filter(
        order=order, product__business__owner=user
    ).exists():
        return CancelledBy.VENDOR
    return None


@transaction.atomic
def cancel_order(*, order_id: UUID, user, reason: str = "", note: str = "") -> Order:
    """
    Cancel an order on behalf of a customer, vendor or admin.

    Rules:
    - Customer: only while unpaid, or paid but the shop has not started on it.
    - Vendor: any time before the goods leave the shop; must give a reason
      (out_of_stock, item_damaged, or other + note).
    - Admin: same window as vendor.
    Stock always returns to the bucket it came from. Paid orders are flagged
    "refund due" for manual refund in the Paystack dashboard.
    """
    order = Order.objects.select_for_update().get(pk=order_id)
    role = _cancel_role(user, order)
    note = (note or "").strip()

    if role is None:
        raise OrderPermissionError("You are not allowed to cancel this order.")
    if order.status == OrderStatus.CANCELLED.value:
        raise OrderFlowError("This order is already cancelled.")

    if role == CancelledBy.CUSTOMER:
        if order.status not in _CUSTOMER_CANCELLABLE:
            raise OrderFlowError(
                "This order can no longer be cancelled because the shop has started "
                "preparing it. Please contact the shop."
            )
        reason = CancellationReason.CUSTOMER_REQUEST
    else:
        if order.status not in _VENDOR_CANCELLABLE:
            raise OrderFlowError("This order can no longer be cancelled.")
        if role == CancelledBy.VENDOR:
            if reason not in _VENDOR_REASONS:
                raise OrderFlowError(
                    "Please choose a reason: out_of_stock, item_damaged or other."
                )
            if reason == CancellationReason.OTHER and not note:
                raise OrderFlowError("Please add a note explaining why the order was cancelled.")
        elif reason not in CancellationReason.values:
            reason = CancellationReason.OTHER

    return _apply_cancellation(order=order, by=role, user=user, reason=reason, note=note)


@transaction.atomic
def cancel_unpaid_order(*, order_id: UUID) -> bool:
    """Cancel an order that was not paid within the payment window. Returns True if cancelled."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        return False
    if _has_successful_payment(order):
        # Payment went through but the order has not been updated yet — leave it.
        return False
    _apply_cancellation(
        order=order,
        by=CancelledBy.SYSTEM,
        user=None,
        reason=CancellationReason.PAYMENT_TIMEOUT,
    )
    return True


def _apply_cancellation(*, order: Order, by: str, user, reason: str, note: str = "") -> Order:
    previous_status = order.status
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = timezone.now()
    order.cancelled_by = by
    order.cancelled_by_user = user
    order.cancellation_reason = reason
    order.cancellation_note = note
    if _has_successful_payment(order):
        order.refund_status = RefundStatus.DUE
    order.save(update_fields=[
        "status", "cancelled_at", "cancelled_by", "cancelled_by_user",
        "cancellation_reason", "cancellation_note", "refund_status", "updated_at",
    ])

    release_order_stock(order=order)

    logger.info(
        "order_cancelled order=%s by=%s reason=%s refund=%s",
        order.pk, by, reason, order.refund_status,
    )

    try:
        from apps.notifications.services.notification_service import notify_order_status_changed
        notify_order_status_changed(order=order, previous_status=previous_status)
    except Exception:
        pass

    return order
