"""
Business member selectors.

Reusable queries for retrieving business members.
"""

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.businesses.models import BusinessMember
from apps.businesses.choices import MemberStatus


def get_members() -> QuerySet[BusinessMember]:
    """
    Return all business members.
    """
    return (
        BusinessMember.objects
        .select_related(
            "business",
            "branch",
            "user",
            "invited_by",
        )
    )


def get_member_by_id(member_id) -> BusinessMember:
    """
    Return a single business member.
    """
    return get_object_or_404(
        get_members(),
        id=member_id,
    )


def get_business_members(business) -> QuerySet[BusinessMember]:
    """
    Return all members belonging to a business.
    """
    return (
        get_members()
        .filter(business=business)
    )


def get_branch_members(branch) -> QuerySet[BusinessMember]:
    """
    Return members assigned to a branch.
    """
    return (
        get_members()
        .filter(branch=branch)
    )


def get_active_members() -> QuerySet[BusinessMember]:
    """
    Return active business members.
    """
    return (
        get_members()
        .filter(
            status=MemberStatus.ACTIVE,
        )
    )

def get_member_by_user(user) -> QuerySet[BusinessMember]:
    """
    Return all memberships for a user.
    """
    return (
        get_members()
        .filter(user=user)
    )


def get_members_by_role(role) -> QuerySet[BusinessMember]:
    """
    Return members having a specific role.
    """
    return (
        get_members()
        .filter(role=role)
    )