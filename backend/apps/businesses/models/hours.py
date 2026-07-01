"""
Business operating hours.

Each Branch can define its operating hours
for every day of the week.
"""

from django.db import models

from core.models import UUIDTimeStampedModel
from businesses.choices import WeekDay
from .branch import Branch


class BusinessHours(UUIDTimeStampedModel):
    """
    Weekly operating hours for a branch.
    """

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="business_hours",
    )

    weekday = models.PositiveSmallIntegerField(
        choices=WeekDay.choices,
    )

    opening_time = models.TimeField()

    closing_time = models.TimeField()

    is_closed = models.BooleanField(
        default=False,
        help_text="Branch is closed on this day.",
    )

    is_twenty_four_hours = models.BooleanField(
        default=False,
        help_text="Open 24 hours.",
    )

    class Meta:
        db_table = "businesses_business_hours"

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

    def __str__(self):
        return (
            f"{self.branch.name} - "
            f"{self.get_weekday_display()}"
        )