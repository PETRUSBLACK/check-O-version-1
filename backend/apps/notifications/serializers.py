from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    What the inbox reads.

    `is_read` is derived rather than stored: the model keeps `read_at` because
    *when* it was read is sometimes worth knowing, but every screen only ever
    asks the yes/no question, and making the app compute `read_at !== null`
    itself is how you end up with three slightly different versions of it.
    """

    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "body",
            "event_type",
            "payload",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "title",
            "body",
            "event_type",
            "payload",
            "created_at",
            "updated_at",
        )

    def get_is_read(self, obj) -> bool:
        return obj.read_at is not None


class UnreadCountSerializer(serializers.Serializer):
    """Just the number on the bell."""

    unread = serializers.IntegerField()
