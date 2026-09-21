"""
AI embedding model.
"""

from django.db import models

from core.models import UUIDTimeStampedModel

from .product import Product


class ProductEmbedding(UUIDTimeStampedModel):

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="embedding",
    )

    ai_description = models.TextField(
        blank=True,
    )

    keywords = models.JSONField(
        default=list,
        blank=True,
    )

    embedding = models.JSONField(
        default=list,
        blank=True,
    )

    embedding_model = models.CharField(
        max_length=100,
        blank=True,
    )

    class Meta:
        db_table = "products_embedding"

    def __str__(self):
        return self.product.name