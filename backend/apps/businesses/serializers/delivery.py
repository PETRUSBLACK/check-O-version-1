from rest_framework import serializers

from apps.businesses.models import DeliveryZone


class DeliveryZoneSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    business_name = serializers.CharField(
        source="branch.business.name",
        read_only=True,
    )

    class Meta:
        model = DeliveryZone

        fields = (
            "id",
            "branch",
            "branch_name",
            "business_name",
            "name",
            "radius_km",
            "delivery_fee",
            "minimum_order_amount",
            "estimated_delivery_time",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )