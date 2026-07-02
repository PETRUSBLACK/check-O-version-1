"""
Business gallery model.

Stores images associated with a business.
"""

from django.db import models
from django.db.models import Q

from core.models import UUIDTimeStampedModel

from .business import Business


class BusinessGallery(UUIDTimeStampedModel):
    """
    Stores gallery images for a business.

    Images may include:
        - Store front
        - Interior
        - Products
        - Restaurant meals
        - Pharmacy shelves
        - Promotional banners
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="gallery",
        help_text="Business this image belongs to.",
    )

    title = models.CharField(
        max_length=150,
        blank=True,
        help_text="Optional image title.",
    )

    image = models.ImageField(
        upload_to="businesses/gallery/",
        help_text="Gallery image.",
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional image description.",
    )

    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Controls the order images are displayed.",
    )

    is_cover = models.BooleanField(
        default=False,
        help_text="Whether this image is the business cover image.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this image is visible to customers.",
    )

    class Meta:
        db_table = "businesses_gallery"
        verbose_name = "Business Gallery"
        verbose_name_plural = "Business Gallery"

        ordering = [
            "display_order",
            "created_at",
        ]

        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["display_order"]),
            models.Index(fields=["is_active"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["business"],
                condition=Q(is_cover=True),
                name="unique_business_cover_image",
            )
        ]

    def __str__(self):
        if self.title:
            return f"{self.business.name} - {self.title}"

        return f"{self.business.name} Gallery Image"

    @property
    def is_visible(self):
        """
        Returns whether the image is visible.
        """
        return self.is_active