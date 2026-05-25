from django.conf import settings
from django.db import models

from core.models import UUIDTimeStampedModel


class AnalyticsEvent(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="analytics_events",
    )
    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "analytics_analyticsevent"
        ordering = ["-created_at"]
