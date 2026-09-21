"""
Product variant serializer.
"""

from rest_framework import serializers

from apps.products.models import ProductVariant


class ProductVariantSerializer(serializers.ModelSerializer):
    """
    Serializer for product variants.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    class Meta:
        model = ProductVariant

        fields = (
            "id",
            "product",
            "product_name",
            "name",
            "value",
            "sku",
            "price_adjustment",
            "stock",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "product_name",
        )