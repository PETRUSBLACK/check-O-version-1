from rest_framework import serializers

from apps.businesses.models import RestaurantProfile


class RestaurantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantProfile

        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )