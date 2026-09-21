"""
Inventory alerts.
"""

from django.db import models

from core.models import UUIDTimeStampedModel

from .product import Product


class InventoryAlert(UUIDTimeStampedModel):

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory_alert",
    )

    threshold = models.PositiveIntegerField(
        default=5,
    )

    email_notification = models.BooleanField(
        default=True,
    )

    in_app_notification = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "products_inventory_alert"

    def __str__(self):
        return self.product.name