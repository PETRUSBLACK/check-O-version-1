"""
Delivery zone model.

Defines the delivery configuration for a business branch.
"""

from django.core.exceptions import ValidationError
from django.db import models

from core.models import UUIDTimeStampedModel

from .branch import Branch


class DeliveryZone(UUIDTimeStampedModel):
    """
    Defines a delivery area for a business branch.

    Example:
        Branch:
            Shoprite Lekki

        Delivery Zones:
            - Lekki Phase 1
            - Ikoyi
            - Victoria Island
    """

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="delivery_zones",
        help_text="Branch this delivery zone belongs to.",
    )

    name = models.CharField(
        max_length=120,
        help_text="Example: Lekki Phase 1",
    )

    radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Maximum delivery radius in kilometres.",
    )

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Delivery charge for this zone.",
    )

    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Minimum order amount before delivery is allowed.",
    )

    free_delivery_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Orders above this amount qualify for free delivery.",
    )

    minimum_delivery_time = models.PositiveIntegerField(
        default=20,
        help_text="Minimum estimated delivery time (minutes).",
    )

    maximum_delivery_time = models.PositiveIntegerField(
        default=45,
        help_text="Maximum estimated delivery time (minutes).",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this delivery zone is currently active.",
    )

    class Meta:
        db_table = "businesses_delivery_zone"
        verbose_name = "Delivery Zone"
        verbose_name_plural = "Delivery Zones"

        ordering = [
            "branch",
            "name",
        ]

        indexes = [
            models.Index(fields=["branch"]),
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                name="unique_delivery_zone_per_branch",
            )
        ]

    def clean(self):
        """
        Validate delivery settings.
        """
        if self.minimum_delivery_time > self.maximum_delivery_time:
            raise ValidationError(
                "Minimum delivery time cannot be greater than maximum delivery time."
            )

        if self.radius_km <= 0:
            raise ValidationError(
                "Delivery radius must be greater than zero."
            )

        if self.delivery_fee < 0:
            raise ValidationError(
                "Delivery fee cannot be negative."
            )

    def __str__(self):
        return f"{self.branch.name} - {self.name}"

    @property
    def estimated_delivery_time(self):
        """
        Human-readable delivery estimate.
        """
        return (
            f"{self.minimum_delivery_time}"
            f"-{self.maximum_delivery_time} mins"
        )