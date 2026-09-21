"""
Inventory movement model.
"""

from django.db import models

from core.models import UUIDTimeStampedModel

from .product import Product


class InventoryMovement(UUIDTimeStampedModel):

    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    ADJUSTMENT = "adjustment"

    MOVEMENT_TYPES = [
        (STOCK_IN, "Stock In"),
        (STOCK_OUT, "Stock Out"),
        (ADJUSTMENT, "Adjustment"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory_movements",
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPES,
    )

    quantity = models.IntegerField()

    note = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = "products_inventory"

        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return f"{self.product.name} ({self.movement_type})"