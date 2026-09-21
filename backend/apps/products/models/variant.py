"""
Product variant model.
"""

from django.db import models

from core.models import UUIDTimeStampedModel

from .product import Product


class ProductVariant(UUIDTimeStampedModel):
    """
    Represents a product variation.

    Examples:
        - Size: XL
        - Color: Red
        - Storage: 256GB
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )

    name = models.CharField(
        max_length=100,
    )

    value = models.CharField(
        max_length=100,
    )

    sku = models.CharField(
        max_length=80,
        unique=True,
    )

    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    stock = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "products_variant"

        ordering = [
            "product",
            "name",
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"