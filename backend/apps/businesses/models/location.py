"""
Business location model.

Stores the geographical location of a business.
"""

from django.db import models

from core.models import UUIDTimeStampedModel

from .business import Business


class BusinessLocation(UUIDTimeStampedModel):
    """
    Stores a business location.
    """

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="location",
    )

    address = models.TextField()

    city = models.CharField(
        max_length=100,
    )

    state = models.CharField(
        max_length=100,
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
        max_digits=10,
        decimal_places=7,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    class Meta:
        db_table = "businesses_location"

        ordering = [
            "business__name",
        ]

        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["state"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return f"{self.business.name} Location"