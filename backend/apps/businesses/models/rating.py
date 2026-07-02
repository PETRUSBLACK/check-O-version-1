"""
Business rating and review model.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import UUIDTimeStampedModel

from .business import Business


class BusinessRating(UUIDTimeStampedModel):
    """
    Customer rating and review for a business.

    Each customer can only review a business once,
    but they can update their review later.
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="ratings",
        help_text="Business being reviewed.",
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_ratings",
        help_text="Customer who submitted the review.",
    )

    score = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        help_text="Rating between 1 and 5.",
    )

    title = models.CharField(
        max_length=150,
        blank=True,
        help_text="Short review title.",
    )

    review = models.TextField(
        blank=True,
        help_text="Detailed customer review.",
    )

    is_verified_purchase = models.BooleanField(
        default=False,
        help_text="Whether the customer actually purchased from this business.",
    )

    is_visible = models.BooleanField(
        default=True,
        help_text="Whether this review is publicly visible.",
    )

    class Meta:
        db_table = "businesses_rating"
        verbose_name = "Business Rating"
        verbose_name_plural = "Business Ratings"

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
            models.Index(fields=["is_visible"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.customer} rated "
            f"{self.business.name} "
            f"{self.score}/5"
        )

    @property
    def is_positive(self):
        """
        Returns True for ratings of 4 or 5.
        """
        return self.score >= 4

    @property
    def is_negative(self):
        """
        Returns True for ratings of 1 or 2.
        """
        return self.score <= 2