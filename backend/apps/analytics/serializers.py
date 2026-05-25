from rest_framework import serializers

from .models import AnalyticsEvent


class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent
        fields = ("id", "user", "event_type", "payload", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")
