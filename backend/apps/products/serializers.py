from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    available_stock = serializers.IntegerField(read_only=True)
    uses_channel_allocation = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "business",
            "name",
            "description",
            "price",
            "stock",
            "smartmall_allocation",
            "available_stock",
            "uses_channel_allocation",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {
            "stock": {
                "help_text": "Total stock in your store (all channels combined)."
            },
            "smartmall_allocation": {
                "help_text": (
                    "Optional. How many units to reserve for SmartMall orders only. "
                    "Leave blank if SmartMall is your only sales channel."
                )
            },
        }
