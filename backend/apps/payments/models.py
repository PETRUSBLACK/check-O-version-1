from django.db import models

from apps.orders.models import Order
from core.models import UUIDTimeStampedModel


class PaymentProvider(models.TextChoices):
    FLUTTERWAVE = "flutterwave", "Flutterwave"
    PAYSTACK = "paystack", "Paystack"
    STRIPE = "stripe", "Stripe"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class Payment(UUIDTimeStampedModel):
    # A payment covers either a single order, or a whole checkout group
    # (one payment for several shop orders).
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
    )
    checkout_group = models.ForeignKey(
        "orders.CheckoutGroup",
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
    )
    provider = models.CharField(max_length=32, choices=PaymentProvider.choices)
    external_ref = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "payments_payment"
        ordering = ["-created_at"]

    def get_orders(self):
        """All orders this payment pays for."""
        if self.checkout_group_id:
            return list(self.checkout_group.orders.all())
        return [self.order] if self.order_id else []
