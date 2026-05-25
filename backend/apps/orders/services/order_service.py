from decimal import Decimal
from typing import Iterable
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.orders.models import FulfilmentType, Order, OrderItem, OrderStatus, StockReservation
from apps.products.models import Product


class OrderFlowError(Exception):
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
        if product.stock < qty:
            raise OrderFlowError("Insufficient stock")
        line_total = product.price * qty
        OrderItem.objects.create(order=order, product=product, quantity=qty, unit_price=product.price)
        total += line_total
        product.stock -= qty
        product.save(update_fields=["stock", "updated_at"])
    order.total = total
    order.save(update_fields=["total", "updated_at"])
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

    # Release stock back
    for item in order.items.select_related("product").all():
        product = Product.objects.select_for_update().get(pk=item.product_id)
        product.stock += item.quantity
        product.save(update_fields=["stock", "updated_at"])

    # Trigger refund
    _initiate_refund_for_expired_order(order=order)

    # Notify customer
    try:
        from apps.notifications.services.notification_service import notify_pickup_expired
        notify_pickup_expired(order=order)
    except Exception:
        pass

    return order


def _initiate_refund_for_expired_order(*, order: Order) -> None:
    """
    Finds the successful payment for this order and marks it for refund.
    In production, this would call the gateway's refund API.
    """
    from apps.payments.models import Payment, PaymentStatus
    payment = Payment.objects.filter(order=order, status=PaymentStatus.SUCCESS).first()
    if payment:
        # In production: call gateway.refund(payment)
        # For now: log the refund intent
        import logging
        logger = logging.getLogger(__name__)
        logger.info("refund_initiated order=%s payment=%s amount=%s", order.pk, payment.pk, payment.amount)
