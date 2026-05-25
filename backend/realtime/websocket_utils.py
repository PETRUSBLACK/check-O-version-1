"""Utility helpers for sending messages over Django Channels layer."""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def send_to_user(user_id: str, event_type: str, payload: dict) -> None:
    """Send a WebSocket event to a specific user's channel group."""
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "send_notification",
            "event": event_type,
            "payload": payload,
        },
    )
