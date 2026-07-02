"""
Business member model.

Represents users that belong to a business.

A member may be assigned to the entire business or to
a specific branch.
"""

from django.conf import settings
from django.db import models

from core.models import UUIDTimeStampedModel

from apps.businesses.choices import (
    BusinessMemberRole,
    MemberStatus,
)

from .business import Business
from .branch import Branch


class BusinessMember(UUIDTimeStampedModel):
    """
    Associates a user with a business.

    Examples:
        - Business Owner
        - Branch Manager
        - Cashier
        - Inventory Manager
        - Delivery Rider
        - Accountant
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="members",
        help_text="Business the member belongs to.",
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        related_name="members",
        null=True,
        blank=True,
        help_text="Leave empty if the member serves all branches.",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="business_memberships",
        help_text="User assigned to this business.",
    )

    role = models.CharField(
        max_length=40,
        choices=BusinessMemberRole.choices,
        db_index=True,
        help_text="System role of the member.",
    )

    job_title = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional business-specific job title.",
    )

    status = models.CharField(
        max_length=20,
        choices=MemberStatus.choices,
        default=MemberStatus.INVITED,
        db_index=True,
        help_text="Current membership status.",
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date the member joined the business.",
    )

    left_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date the member left the business.",
    )

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_invitations",
        help_text="User that invited this member.",
    )

    class Meta:
        db_table = "businesses_member"
        verbose_name = "Business Member"
        verbose_name_plural = "Business Members"

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
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.get_role_display()} "
            f"({self.business.name})"
        )

    @property
    def is_owner(self):
        return self.role == BusinessMemberRole.OWNER

    @property
    def is_manager(self):
        return self.role == BusinessMemberRole.MANAGER

    @property
    def is_cashier(self):
        return self.role == BusinessMemberRole.CASHIER

    @property
    def is_inventory_manager(self):
        return self.role == BusinessMemberRole.INVENTORY_MANAGER

    @property
    def is_delivery_manager(self):
        return self.role == BusinessMemberRole.DELIVERY_MANAGER

    @property
    def is_delivery_rider(self):
        return self.role == BusinessMemberRole.DELIVERY_RIDER

    @property
    def is_accountant(self):
        return self.role == BusinessMemberRole.ACCOUNTANT

    @property
    def is_support(self):
        return self.role == BusinessMemberRole.SUPPORT

    @property
    def is_active(self):
        return self.status == MemberStatus.ACTIVE

    @property
    def is_invited(self):
        return self.status == MemberStatus.INVITED

    @property
    def is_suspended(self):
        return self.status == MemberStatus.SUSPENDED

    @property
    def is_removed(self):
        return self.status == MemberStatus.REMOVED