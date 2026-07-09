"""
Business member services.

Contains business logic for managing business members.
"""

from django.db import transaction
from django.utils import timezone

from apps.businesses.models import BusinessMember
from apps.businesses.choices import MemberStatus


@transaction.atomic
def create_member(*, invited_by=None, **validated_data):
    """
    Create a new business member.
    """

    return BusinessMember.objects.create(
        invited_by=invited_by,
        **validated_data,
    )


@transaction.atomic
def update_member(*, member, **validated_data):
    """
    Update an existing business member.
    """

    for field, value in validated_data.items():
        setattr(member, field, value)

    member.save()

    return member


@transaction.atomic
def activate_member(*, member):
    """
    Activate a business member.
    """

    member.status = MemberStatus.ACTIVE
    member.save(update_fields=["status"])

    return member


@transaction.atomic
def suspend_member(*, member):
    """
    Suspend a business member.
    """

    member.status = MemberStatus.SUSPENDED
    member.save(update_fields=["status"])

    return member


@transaction.atomic
def remove_member(*, member):
    """
    Remove a business member.
    """

    member.status = MemberStatus.REMOVED
    member.left_at = timezone.now()

    member.save(
        update_fields=[
            "status",
            "left_at",
        ]
    )

    return member