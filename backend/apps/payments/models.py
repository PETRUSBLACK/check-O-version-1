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
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payments",
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
