"""
Stock holds for orders.

Every unit an order takes is recorded as a StockReservation that remembers which
bucket it came from (the SmartMall allocation or the main stock). Whenever stock
has to go back — unpaid in time, cancelled, pickup expired — it goes back to that
same bucket, so the shop's physical count is never inflated.
"""

import logging
from datetime import timedelta
from typing import Iterable, Optional

from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, OrderStatus, StockReservation, StockSource
from apps.products.models import Product

logger = logging.getLogger(__name__)

# How long an unpaid order holds its stock.
PAYMENT_WINDOW_MINUTES = 30


def reserve_stock(*, order: Order, product: Product, quantity: int) -> StockReservation:
    """
    Take `quantity` units for `order` and record where they came from.
    `product` must already be locked with select_for_update() by the caller.
    """
    if product.uses_channel_allocation:
        product.smartmall_allocation = max(0, product.smartmall_allocation - quantity)
        product.save(update_fields=["smartmall_allocation", "updated_at"])
        source = StockSource.ALLOCATION
    else:
        product.stock = max(0, product.stock - quantity)
        product.save(update_fields=["stock", "updated_at"])
        source = StockSource.STOCK

    return StockReservation.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        source=source,
        expires_at=timezone.now() + timedelta(minutes=PAYMENT_WINDOW_MINUTES),
    )


def _return_units(*, product_id, quantity: int, source: str) -> None:
    product = Product.objects.select_for_update().get(pk=product_id)
    if source == StockSource.ALLOCATION and product.smartmall_allocation is not None:
        product.smartmall_allocation += quantity
        product.save(update_fields=["smartmall_allocation", "updated_at"])
    else:
        # Main stock — or the vendor has since switched the allocation off
        product.stock += quantity
        product.save(update_fields=["stock", "updated_at"])


@transaction.atomic
def release_order_stock(*, order: Order) -> int:
    """
    Return all of an order's held stock to where it came from.
    Safe to call more than once — each reservation is only released once.
    Returns the number of units released.
    """
    reservations = list(
        StockReservation.objects.select_for_update().filter(order=order, released=False)
    )

    if not reservations and not StockReservation.objects.filter(order=order).exists():
        # Order created before stock holds existed: fall back to its line items.
        units = 0
        for item in order.items.all():
            product = Product.objects.get(pk=item.product_id)
            source = StockSource.ALLOCATION if product.uses_channel_allocation else StockSource.STOCK
            _return_units(product_id=item.product_id, quantity=item.quantity, source=source)
            units += item.quantity
        return units

    units = 0
    for reservation in reservations:
        _return_units(
            product_id=reservation.product_id,
            quantity=reservation.quantity,
            source=reservation.source,
        )
        reservation.released = True
        reservation.save(update_fields=["released", "updated_at"])
        units += reservation.quantity
    return units


def confirm_order_stock(*, order: Order) -> None:
    """Payment succeeded — the held units are now sold."""
    StockReservation.objects.filter(order=order, released=False, confirmed=False).update(
        confirmed=True, updated_at=timezone.now()
    )


def release_expired_holds(*, product_ids: Optional[Iterable] = None) -> int:
    """
    Cancel unpaid orders whose 30-minute payment window has passed and return
    their stock. Run by the background job, and also just before add-to-cart /
    checkout for the products involved, so stock never stays stuck even if the
    background job is late.
    Returns the number of orders cancelled.
    """
    from apps.orders.services.order_service import cancel_unpaid_order

    expired = StockReservation.objects.filter(
        confirmed=False,
        released=False,
        expires_at__lt=timezone.now(),
        order__status=OrderStatus.PENDING_PAYMENT,
    )
    if product_ids is not None:
        expired = expired.filter(product_id__in=list(product_ids))

    order_ids = set(expired.values_list("order_id", flat=True))
    cancelled = 0
    for order_id in order_ids:
        try:
            if cancel_unpaid_order(order_id=order_id):
                cancelled += 1
        except Exception:
            logger.exception("release_expired_hold_failed order=%s", order_id)
    return cancelled
