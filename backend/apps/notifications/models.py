from django.conf import settings
from django.db import models

from core.models import UUIDTimeStampedModel


class Notification(UUIDTimeStampedModel):
    """
    One message to one person.

    `event_type` and `payload` exist so a notification can be acted on and not
    only read. Every caller of `notify()` was already working out which order or
    shop or product the message was about and passing it along; until 2026-10-10
    the row kept only the words and threw the rest away, so an inbox could show
    "Order Update: Shipped" and had no way to open the order it meant.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # e.g. "order.status_changed", "business.approved", "inventory.low_stock".
    event_type = models.CharField(max_length=64, blank=True, default="")
    # The ids the event refers to: {"order_id": "...", "business_id": "..."}.
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [
            # The badge asks "how many unread for this person?" on every screen.
            models.Index(fields=["user", "read_at"], name="notif_user_read_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} → {self.user_id}"
