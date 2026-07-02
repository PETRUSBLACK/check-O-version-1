"""
Business verification model.

Stores regulatory and verification information for a business.
"""

from django.conf import settings
from django.db import models

from core.models import UUIDTimeStampedModel

from apps.businesses.choices import VerificationStatus

from .business import Business


class BusinessVerification(UUIDTimeStampedModel):
    """
    Stores business verification information.

    Every business has at most one verification record.
    """

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="verification",
    )

    legal_name = models.CharField(
        max_length=255,
        help_text="Registered legal business name.",
    )

    registration_number = models.CharField(
        max_length=120,
        help_text="CAC or official registration number.",
    )

    tax_identifier = models.CharField(
        max_length=120,
        blank=True,
        help_text="Tax Identification Number (TIN) or VAT number.",
    )

    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date verification request was submitted.",
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date verification was approved.",
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_businesses",
    )

    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejecting the verification request.",
    )

    notes = models.TextField(
        blank=True,
        help_text="Internal administrative notes.",
    )

    class Meta:
        db_table = "businesses_verification"
        verbose_name = "Business Verification"
        verbose_name_plural = "Business Verifications"

    def __str__(self):
        return f"{self.business.name} ({self.get_status_display()})"

    @property
    def is_verified(self):
        return self.status == VerificationStatus.APPROVED

    @property
    def is_pending(self):
        return self.status == VerificationStatus.PENDING

    @property
    def is_rejected(self):
        return self.status == VerificationStatus.REJECTED