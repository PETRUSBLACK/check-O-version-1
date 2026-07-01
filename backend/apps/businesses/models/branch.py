"""
Branch model.

A Branch represents a physical location of a business.

Examples:

Shoprite
    ├── Lekki Branch
    ├── Ikeja Branch
    └── Abuja Branch
"""

from django.db import models

from core.models import UUIDTimeStampedModel
from .business import Business


class Branch(UUIDTimeStampedModel):
    """
    Physical location of a business.

    Inventory, staff, orders and operating hours
    belong to a Branch.
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="branches",
    )

    name = models.CharField(
        max_length=255,
        help_text="Example: Lekki Branch",
    )

    branch_code = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    phone_number = models.CharField(
        max_length=30,
        blank=True,
    )

    manager_name = models.CharField(
        max_length=255,
        blank=True,
    )

    full_address = models.TextField()

    city = models.CharField(
        max_length=100,
        db_index=True,
    )

    state = models.CharField(
        max_length=100,
        db_index=True,
    )

    country = models.CharField(
        max_length=100,
        default="Nigeria",
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    is_active = models.BooleanField(
        default=True,
    )

    accepts_walk_in = models.BooleanField(
        default=True,
    )

    supports_delivery = models.BooleanField(
        default=True,
    )

    supports_pickup = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "businesses_branch"
        ordering = ["business", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["business", "name"],
                name="unique_branch_name_per_business",
            )
        ]

        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["city"]),
            models.Index(fields=["state"]),
            models.Index(fields=["country"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.business.name} - {self.name}"

    @property
    def coordinates(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
        }