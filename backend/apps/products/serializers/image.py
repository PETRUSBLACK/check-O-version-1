"""
Product image serializer.
"""

from rest_framework import serializers

from apps.products.models import ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for product images.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    business = serializers.UUIDField(
        source="product.business.id",
        read_only=True,
    )

    class Meta:
        model = ProductImage

        fields = (
            "id",
            "product",
            "product_name",
            "business",
            "image",
            "alt_text",
            "is_cover",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "product_name",
            "business",
        )