from rest_framework import serializers
from .models import ProductPromotion


class ProductPromotionSerializer(serializers.ModelSerializer):
    discounted_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_currently_active = serializers.BooleanField(read_only=True)
    ctr = serializers.FloatField(read_only=True)

    class Meta:
        model = ProductPromotion
        fields = (
            "id", "product", "title", "promotion_type",
            "boost_weight", "discount_percent", "discounted_price",
            "starts_at", "ends_at", "is_active", "is_currently_active",
            "budget", "impressions", "clicks", "ctr",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "impressions", "clicks", "ctr",
            "discounted_price", "is_currently_active",
            "created_at", "updated_at",
        )
