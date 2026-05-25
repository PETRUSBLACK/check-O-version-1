from rest_framework import serializers
from .models import SubscriptionPlan, VendorSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = (
            "id", "name", "slug", "tier", "price_monthly",
            "max_products", "max_promotions", "featured_listing",
            "analytics_access", "priority_support", "is_active",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class VendorSubscriptionSerializer(serializers.ModelSerializer):
    plan_detail = SubscriptionPlanSerializer(source="plan", read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = VendorSubscription
        fields = (
            "id", "business", "plan", "plan_detail",
            "status", "is_active", "days_remaining",
            "started_at", "expires_at", "auto_renew", "cancelled_at",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "status", "started_at", "expires_at", "cancelled_at", "created_at", "updated_at")
