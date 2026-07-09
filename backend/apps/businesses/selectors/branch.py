"""
Branch selectors.

Contains reusable query functions for retrieving
branch-related data.
"""

from django.shortcuts import get_object_or_404
from django.db.models import QuerySet

from apps.businesses.models import Branch


def get_branches() -> QuerySet[Branch]:
    """
    Return all branches.
    """

    return (
        Branch.objects
        .select_related("business")
        .all()
    )


def get_active_branches() -> QuerySet[Branch]:
    """
    Return active branches.
    """

    return (
        get_branches()
        .filter(is_active=True)
    )


def get_branch_by_id(branch_id) -> Branch:
    """
    Return a single branch.
    """

    return get_object_or_404(
        get_branches(),
        id=branch_id,
    )


def get_business_branches(business) -> QuerySet[Branch]:
    """
    Return all branches belonging to a business.
    """

    return (
        get_active_branches()
        .filter(business=business)
    )


def get_branches_by_city(city: str) -> QuerySet[Branch]:
    """
    Return branches in a city.
    """

    return (
        get_active_branches()
        .filter(city__iexact=city)
    )


def get_branches_by_state(state: str) -> QuerySet[Branch]:
    """
    Return branches in a state.
    """

    return (
        get_active_branches()
        .filter(state__iexact=state)
    )


def search_branches(query: str) -> QuerySet[Branch]:
    """
    Search branches by name.
    """

    return (
        get_active_branches()
        .filter(name__icontains=query)
    )

def get_business_branches(business) -> QuerySet[Branch]:
    """
    Return active branches for a business.
    """
    return (
        get_active_branches()
        .filter(business=business)
    )


def list_business_branches(*, business) -> QuerySet[Branch]:
    """
    Return all branches for a business,
    including inactive ones.
    """
    return (
        get_branches()
        .filter(business=business)
    )