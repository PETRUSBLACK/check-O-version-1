"""
Telling a shop when something is running out.

A vendor losing a sale because she didn't know she was down to her last two bags
is a bad way to find out. This watches available stock against each product's
`low_stock_threshold` and tells the shop owner.

Two rules make the difference between useful and muted:

1. **Once per fall, not once per check.** The checker runs every five minutes.
   Without state, Grace would get the same message 288 times a day. Each product
   records when it was told; the record is cleared only when the item is restocked
   above its threshold, so the next fall can speak again.

2. **One message per shop, not one per product.** A shop that restocks on Fridays
   might have eight items low at once. Eight notifications is noise; one saying
   "8 items are running low" with the first few named is a to-do list.

What counts as "available" is `Product.available_stock` — the same number a
shopper sees. A product that sets some stock aside for Check-O is low when its
Check-O portion is low, which is the portion that can actually disappear without
the owner noticing.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.products.models import Product

logger = logging.getLogger(__name__)

# How many items to name in the message before saying "and N more".
NAMES_IN_MESSAGE = 3


def check_low_stock() -> int:
    """
    Tell each shop about items that have just fallen to or below their threshold,
    and forget the ones that have been restocked.

    Returns the number of shops notified.
    """
    _clear_restocked()
    return _notify_fallen()


def _clear_restocked() -> int:
    """
    A product back above its threshold is no longer low, so it may be reported
    again next time it falls. Done first, so a restock-then-fall inside one
    interval is still reported.
    """
    cleared = 0
    candidates = Product.objects.filter(low_stock_notified_at__isnull=False).only(
        "id", "stock", "smartmall_allocation", "low_stock_threshold"
    )
    for product in candidates:
        if product.available_stock > product.low_stock_threshold:
            Product.objects.filter(pk=product.pk).update(low_stock_notified_at=None)
            cleared += 1
    return cleared


def _notify_fallen() -> int:
    """Group newly-low products by shop and send one message to each owner."""
    # available_stock is a Python property (it is min(stock, allocation) when the
    # shop sets some aside), so the comparison can't be pushed into SQL. Narrow
    # as far as the database can, then check the rest in Python.
    candidates = (
        Product.objects.filter(
            is_active=True,
            business__status="approved",
            low_stock_notified_at__isnull=True,
        )
        .select_related("business", "business__owner")
        .only(
            "id",
            "name",
            "stock",
            "smartmall_allocation",
            "low_stock_threshold",
            "business__name",
            "business__owner",
        )
    )

    by_shop: dict = {}
    for product in candidates:
        if product.available_stock <= product.low_stock_threshold:
            by_shop.setdefault(product.business_id, []).append(product)

    shops_told = 0
    for products in by_shop.values():
        if _tell_shop(products):
            shops_told += 1

    if shops_told:
        logger.info("low_stock_notified shops=%d", shops_told)
    return shops_told


def _tell_shop(products: list) -> bool:
    """One message to one owner. Returns True if it was sent."""
    from apps.notifications.services.notification_service import notify

    shop = products[0].business
    owner = shop.owner
    if owner is None:
        return False

    # Emptiest first — that's the order the shop should act in.
    products.sort(key=lambda p: p.available_stock)
    sold_out = [p for p in products if p.available_stock <= 0]

    title = _title(products, sold_out)
    body = _body(products)

    try:
        notify(
            user=owner,
            title=title,
            body=body,
            event_type="inventory.low_stock",
            payload={
                "business_id": str(shop.id),
                "product_ids": [str(p.id) for p in products],
                "count": len(products),
                "sold_out": len(sold_out),
            },
        )
    except Exception:  # noqa: BLE001 — a failed message must not stop the rest
        logger.exception("low_stock_notify_failed shop=%s", shop.pk)
        return False

    # Only mark them told once the message actually went.
    stamp = timezone.now()
    with transaction.atomic():
        Product.objects.filter(pk__in=[p.pk for p in products]).update(
            low_stock_notified_at=stamp
        )
    return True


def _title(products: list, sold_out: list) -> str:
    if len(products) == 1:
        product = products[0]
        if product.available_stock <= 0:
            return f"{product.name} has finished"
        return f"{product.name} is running low"
    if sold_out and len(sold_out) == len(products):
        return f"{len(products)} items have finished"
    return f"{len(products)} items are running low"


def _body(products: list) -> str:
    """Name the first few with their numbers, then count the rest."""
    named = products[:NAMES_IN_MESSAGE]
    lines = [
        f"{p.name}: {'none left' if p.available_stock <= 0 else f'{p.available_stock} left'}"
        for p in named
    ]
    remaining = len(products) - len(named)
    if remaining > 0:
        lines.append(f"and {remaining} more")
    return " · ".join(lines)
