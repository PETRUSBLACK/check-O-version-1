from django.conf import settings
from django.db import models

from core.models import UUIDTimeStampedModel


class AssistantType(models.TextChoices):
    CUSTOMER = "customer", "Customer Shopping Assistant"
    VENDOR = "vendor", "Vendor Business Assistant"


class AIConversation(UUIDTimeStampedModel):
    """
    Stores AI assistant conversation history per user.
    Allows multi-turn conversations to maintain context.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    assistant_type = models.CharField(
        max_length=20,
        choices=AssistantType.choices,
        default=AssistantType.CUSTOMER,
    )
    title = models.CharField(max_length=255, blank=True)
    history = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ai_conversation"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.email} — {self.assistant_type} ({self.created_at.strftime('%d %b %Y')})"

    @property
    def message_count(self):
        return len([m for m in self.history if m.get("role") == "user"])
