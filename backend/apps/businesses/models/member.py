"""
Business member models.

Represents users that are associated with a business.
"""

from django.conf import settings
from django.db import models

from core.models import UUIDTimeStampedModel
from businesses.choices import BusinessMemberRole
from .business import Business
from .branch import Branch


class BusinessMember(UUIDTimeStampedModel):
    """
    Associates a user with a business.

    A member may belong to the entire business or
    be assigned to a specific branch.
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="members",
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        related_name="members",
        null=True,
        blank=True,
        help_text="Leave empty if member serves all branches.",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_memberships",
    )

    role = models.CharField(
        max_length=40,
        choices=BusinessMemberRole.choices,
    )

    is_active = models.BooleanField(
        default=True,
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_invitations",
    )

    class Meta:
        db_table = "businesses_member"

        ordering = [
            "business",
            "role",
            "user",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "business",
                    "user",
                ],
                name="unique_business_member",
            )
        ]

        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["branch"]),
            models.Index(fields=["user"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.role} ({self.business})"

    @property
    def is_owner(self):
        return self.role == BusinessMemberRole.OWNER

    @property
    def is_manager(self):
        return self.role == BusinessMemberRole.MANAGER