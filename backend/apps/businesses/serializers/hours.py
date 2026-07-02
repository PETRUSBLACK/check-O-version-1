from rest_framework import serializers

from apps.businesses.models import BusinessHours


class BusinessHoursSerializer(serializers.ModelSerializer):
    weekday_name = serializers.CharField(
        source="get_weekday_display",
        read_only=True,
    )

    class Meta:
        model = BusinessHours

        fields = (
            "id",
            "branch",
            "weekday",
            "weekday_name",
            "opening_time",
            "closing_time",
            "is_closed",
            "is_twenty_four_hours",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )