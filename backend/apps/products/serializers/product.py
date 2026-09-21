from rest_framework import serializers

from apps.products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    available_stock = serializers.SerializerMethodField()
    uses_channel_allocation = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = (
            "id",
            "business",
            "category",
            "name",
            "slug",
            "sku",
            "barcode",
            "description",
            "currency",
            "cost_price",
            "price",
            "stock",
            "smartmall_allocation",
            "available_stock",
            "uses_channel_allocation",
            "low_stock_threshold",
            "is_active",
            "is_featured",
            "is_published",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
        )

    def get_available_stock(self, obj):
        if obj.smartmall_allocation is not None:
            return obj.smartmall_allocation
        return obj.stock

    def get_uses_channel_allocation(self, obj):
        return obj.smartmall_allocation is not None