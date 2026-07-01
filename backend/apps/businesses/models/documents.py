"""
Business documents.
"""

from django.db import models

from core.models import UUIDTimeStampedModel
from .business import Business


class BusinessDocument(UUIDTimeStampedModel):

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="documents",
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

    is_verified = models.BooleanField(
        default=False,
    )

    class Meta:
        db_table = "businesses_documents"

    def __str__(self):
        return self.title