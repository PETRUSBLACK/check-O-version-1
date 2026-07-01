"""
Business verification records.
"""

from django.db import models

from core.models import UUIDTimeStampedModel
from .business import Business


class BusinessVerification(UUIDTimeStampedModel):

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="verification",
    )

    legal_name = models.CharField(
        max_length=255,
    )

    registration_number = models.CharField(
        max_length=120,
    )

    tax_identifier = models.CharField(
        max_length=120,
        blank=True,
    )

    verified = models.BooleanField(default=False)

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_businesses",
    )

    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "businesses_verification"

    def __str__(self):
        return self.business.name