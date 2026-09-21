"""
Product image model.
"""

from django.db import models

from core.models import UUIDTimeStampedModel

from .product import Product


class ProductImage(UUIDTimeStampedModel):
    """
    Stores product images.

    A product can have multiple images.

    One image may be marked as the cover image.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="products/images/",
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    is_cover = models.BooleanField(
        default=False,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "products_image"

        ordering = [
            "display_order",
            "created_at",
        ]

        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["is_cover"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.product.name} Image"