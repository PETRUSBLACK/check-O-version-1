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


class StockReservation(UUIDTimeStampedModel):
    """
    Reserves stock at checkout — permanently deducted only on payment confirmation.
    Expires if payment is not received within the window.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reservations")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reservations")
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    confirmed = models.BooleanField(default=False)
    released = models.BooleanField(default=False)

    class Meta:
        db_table = "orders_stockreservation"

    def is_expired(self):
        return not self.confirmed and not self.released and timezone.now() > self.expires_at
