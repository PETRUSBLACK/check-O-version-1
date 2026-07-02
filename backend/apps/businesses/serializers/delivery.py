from rest_framework import serializers

from apps.businesses.models import DeliveryZone


class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone

        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )