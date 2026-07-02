"""
Business document model.

Stores uploaded regulatory and supporting documents for businesses.
"""

from django.conf import settings
from django.db import models

from core.models import UUIDTimeStampedModel

from apps.businesses.choices import BusinessDocumentType

from .business import Business


class BusinessDocument(UUIDTimeStampedModel):
    """
    Stores uploaded business documents.

    Examples:
        - CAC Certificate
        - Tax Certificate
        - Food License
        - Pharmacy License
        - Insurance
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    document_type = models.CharField(
        max_length=50,
        choices=BusinessDocumentType.choices,
    )

    title = models.CharField(
        max_length=150,
    )

    file = models.FileField(
        upload_to="businesses/documents/",
    )

    description = models.TextField(
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_business_documents",
    )

    expiry_date = models.DateField(
        null=True,
        blank=True,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_business_documents",
    )

    class Meta:
        db_table = "businesses_documents"
        verbose_name = "Business Document"
        verbose_name_plural = "Business Documents"

        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return f"{self.business.name} - {self.title}"

    @property
    def has_expired(self):
        """
        Returns True if the document has expired.
        """
        from django.utils import timezone

        if self.expiry_date is None:
            return False

        return self.expiry_date < timezone.localdate()