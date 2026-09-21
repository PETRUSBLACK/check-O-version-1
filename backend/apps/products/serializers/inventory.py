"""
Inventory movement serializer.
"""

from rest_framework import serializers

from apps.products.models import InventoryMovement


class InventoryMovementSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory movements.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    class Meta:
        model = InventoryMovement

        fields = (
            "id",
            "product",
            "product_name",
            "movement_type",
            "quantity",
            "note",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "product_name",
        )