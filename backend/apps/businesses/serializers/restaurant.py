from rest_framework import serializers

from apps.businesses.models import RestaurantProfile


class RestaurantProfileSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source="business.name",
        read_only=True,
    )

    class Meta:
        model = RestaurantProfile

        fields = (
            "id",
            "business",
            "business_name",
            "cuisine",
            "average_preparation_time",
            "accepts_reservations",
            "accepts_takeaway",
            "accepts_delivery",
            "serves_breakfast",
            "serves_lunch",
            "serves_dinner",
            "has_wifi",
            "has_parking",
            "has_outdoor_seating",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )