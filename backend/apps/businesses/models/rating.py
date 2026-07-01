"""
Business rating and review models.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import UUIDTimeStampedModel
from .business import Business


class BusinessRating(UUIDTimeStampedModel):
    """
    Customer rating and review for a business.
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="ratings",
    )

    customer = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="business_ratings",
    )

    score = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        help_text="Rating score between 1 and 5.",
    )

    review = models.TextField(
        blank=True,
        help_text="Optional written review.",
    )

    is_visible = models.BooleanField(
        default=True,
        help_text="Hide inappropriate reviews without deleting them.",
    )

    class Meta:
        db_table = "businesses_rating"

        ordering = [
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "business",
                    "customer",
                ],
                name="unique_customer_business_rating",
            )
        ]

        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["score"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.business.name} ({self.score}/5)"