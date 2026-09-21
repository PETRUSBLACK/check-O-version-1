from django.db import models

from core.models import UUIDTimeStampedModel


class ProductCategory(UUIDTimeStampedModel):
    """
    Hierarchical product categories.

    Example

    Electronics
        Phones
            Android

    Fashion
        Men
            Shoes
    """

    name = models.CharField(
        max_length=120,
        unique=True,
    )

    slug = models.SlugField(
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    icon = models.CharField(
        max_length=80,
        blank=True,
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    is_active = models.BooleanField(
        default=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        db_table = "products_category"

        ordering = [
            "display_order",
            "name",
        ]

    def __str__(self):
        return self.name