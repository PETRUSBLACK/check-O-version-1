import random
import string
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.products.models import Product
from core.models import UUIDTimeStampedModel


class OrderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_PAYMENT = "pending_payment", "Pending payment"
    PAID = "paid", "Paid"
    PROCESSING = "processing", "Processing"
    PACKAGING = "packaging", "Packaging"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    # Pickup-specific statuses
    READY_FOR_PICKUP = "ready_for_pickup", "Ready for pickup"
    COLLECTED = "collected", "Collected"
    EXPIRED = "expired", "Expired"


class FulfilmentType(models.TextChoices):
    DELIVERY = "delivery", "Home Delivery"
    PICKUP = "pickup", "Pick Up In Store"


class CancelledBy(models.TextChoices):
    CUSTOMER = "customer", "Customer"
    VENDOR = "vendor", "Vendor"
    ADMIN = "admin", "Admin"
    SYSTEM = "system", "System"


class CancellationReason(models.TextChoices):
    CUSTOMER_REQUEST = "customer_request", "Customer changed their mind"
    OUT_OF_STOCK = "out_of_stock", "Out of stock"
    ITEM_DAMAGED = "item_damaged", "Item damaged"
    PAYMENT_TIMEOUT = "payment_timeout", "Not paid within the payment window"
    OTHER = "other", "Other"


class RefundStatus(models.TextChoices):
    NONE = "none", "No refund needed"
    DUE = "due", "Refund due"
    REFUNDED = "refunded", "Refunded"


def _generate_pickup_code():
    return "SM-" + "".join(random.choices(string.digits, k=4))


class Order(UUIDTimeStampedModel):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Fulfilment
    fulfilment_type = models.CharField(
        max_length=20,
        choices=FulfilmentType.choices,
        default=FulfilmentType.DELIVERY,
    )
    delivery_address = models.TextField(blank=True)

    # Pickup fields
    pickup_code = models.CharField(max_length=10, blank=True)
    pickup_deadline = models.DateTimeField(null=True, blank=True)

    # Payment / vendor follow-up
    paid_at = models.DateTimeField(null=True, blank=True)
    vendor_reminder_sent_at = models.DateTimeField(null=True, blank=True)

    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.CharField(max_length=20, choices=CancelledBy.choices, blank=True)
    cancelled_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_orders",
    )
    cancellation_reason = models.CharField(max_length=30, choices=CancellationReason.choices, blank=True)
    cancellation_note = models.TextField(blank=True)

    # Refunds are processed manually in the Paystack dashboard, then ticked off in admin
    refund_status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.NONE,
    )
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "orders_order"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return str(self.id)

    def set_pickup_deadline(self, hours: int = 48):
        self.pickup_deadline = timezone.now() + timezone.timedelta(hours=hours)

    def generate_pickup_code(self):
        self.pickup_code = _generate_pickup_code()


class OrderItem(UUIDTimeStampedModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "orders_orderitem"

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class StockSource(models.TextChoices):
    ALLOCATION = "allocation", "SmartMall allocation"
    STOCK = "stock", "Main stock"


class StockReservation(UUIDTimeStampedModel):
    """
    Stock held for an order at checkout.
    - confirmed=True once payment succeeds (the units are sold).
    - released=True once the units have been returned to `source`
      (unpaid in time, cancelled, or pickup expired).
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reservations")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reservations")
    quantity = models.PositiveIntegerField()
    source = models.CharField(
        max_length=20,
        choices=StockSource.choices,
        default=StockSource.STOCK,
        help_text="Which stock bucket the units were taken from, so they go back to the same place.",
    )
    expires_at = models.DateTimeField()
    confirmed = models.BooleanField(default=False)
    released = models.BooleanField(default=False)

    class Meta:
        db_table = "orders_stockreservation"

    def is_expired(self):
        return not self.confirmed and not self.released and timezone.now() > self.expires_at


class RefundQueue(Order):
    """Admin-only view of paid orders that were cancelled and still need a refund."""

    class Meta:
        proxy = True
        verbose_name = "Refund to process"
        verbose_name_plural = "Refunds to process"
