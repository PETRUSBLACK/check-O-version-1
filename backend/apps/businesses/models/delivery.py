"""
Delivery zones for business branches.
"""

from django.db import models

from core.models import UUIDTimeStampedModel
from .branch import Branch


class DeliveryZone(UUIDTimeStampedModel):
    """
    Defines delivery settings for a branch.
    """

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="delivery_zones",
    )

    name = models.CharField(
        max_length=120,
        help_text="Example: Lekki Phase 1",
    )

    radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    estimated_delivery_time = models.PositiveIntegerField(
        help_text="Minutes",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "businesses_delivery_zone"

        ordering = [
            "branch",
            "name",
        ]

    def __str__(self):
        return f"{self.branch.name} - {self.name}"