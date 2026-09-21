"""
Inventory alert serializer.
"""

from rest_framework import serializers

from apps.products.models import InventoryAlert


class InventoryAlertSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory alerts.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    class Meta:
        model = InventoryAlert

        fields = (
            "id",
            "product",
            "product_name",
            "threshold",
            "email_notification",
            "in_app_notification",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "product_name",
        )