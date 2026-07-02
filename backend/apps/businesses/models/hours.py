"""
Business operating hours.

Each branch can define its operating hours
for every day of the week.
"""

from django.core.exceptions import ValidationError
from django.db import models

from core.models import UUIDTimeStampedModel
from apps.businesses.choices import WeekDay

from .branch import Branch


class BusinessHours(UUIDTimeStampedModel):
    """
    Weekly operating hours for a business branch.
    """

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="business_hours",
        help_text="Branch these operating hours belong to.",
    )

    weekday = models.PositiveSmallIntegerField(
        choices=WeekDay.choices,
        db_index=True,
    )

    opening_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Opening time. Leave empty if the branch is closed.",
    )

    closing_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Closing time. Leave empty if the branch is closed.",
    )

    is_closed = models.BooleanField(
        default=False,
        help_text="Whether the branch is closed on this day.",
    )

    is_twenty_four_hours = models.BooleanField(
        default=False,
        help_text="Whether the branch operates 24 hours.",
    )

    class Meta:
        db_table = "businesses_business_hours"
        verbose_name = "Business Hours"
        verbose_name_plural = "Business Hours"

        ordering = [
            "branch",
            "weekday",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "branch",
                    "weekday",
                ],
                name="unique_branch_weekday",
            )
        ]

        indexes = [
            models.Index(fields=["branch"]),
            models.Index(fields=["weekday"]),
        ]

    def clean(self):
        """
        Validate operating hours.
        """
        if self.is_closed:
            return

        if self.is_twenty_four_hours:
            return

        if not self.opening_time or not self.closing_time:
            raise ValidationError(
                "Opening and closing times are required unless the branch is closed or operates 24 hours."
            )

        if self.opening_time >= self.closing_time:
            raise ValidationError(
                "Opening time must be earlier than closing time."
            )

    def __str__(self):
        return (
            f"{self.branch.name} - "
            f"{self.get_weekday_display()}"
        )