"""
Business gallery models.
"""

from django.db import models

from core.models import UUIDTimeStampedModel
from .business import Business


class BusinessGallery(UUIDTimeStampedModel):
    """
    Images associated with a business.
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="gallery",
    )

    image = models.ImageField(
        upload_to="businesses/gallery/",
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "businesses_gallery"

        ordering = [
            "display_order",
            "created_at",
        ]

        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["display_order"]),
        ]

    def __str__(self):
        return f"{self.business.name} Image"