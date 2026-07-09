"""
Business selectors.

Contains reusable query functions for retrieving
business-related data.
"""

from django.db.models import QuerySet

from apps.businesses.models import Business
from apps.businesses.choices import BusinessStatus
from django.shortcuts import get_object_or_404


def get_businesses() -> QuerySet[Business]:
    """
    Return all businesses.
    """

    return (
        Business.objects
        .select_related("owner")
        .all()
    )

def get_active_businesses() -> QuerySet[Business]:
    """
    Return all active businesses.
    """

    return (
        get_businesses()
        .filter(is_active=True)
    )

def get_approved_businesses() -> QuerySet[Business]:
    """
    Return approved businesses.
    """

    return (
        get_active_businesses()
        .filter(
            status=BusinessStatus.APPROVED,
        )
    )

def get_business_by_id(business_id):
    return get_object_or_404(
        get_businesses(),
        id=business_id,
    )

    
def get_user_businesses(user):
    """
    Return businesses owned by a user.
    """

    return (
        get_businesses()
        .filter(owner=user)
    )

def search_businesses(query):
    """
    Search businesses by name.
    """

    return (
        get_approved_businesses()
        .filter(
            name__icontains=query,
        )
    )

def get_businesses_by_category(category):
    """
    Return businesses in a category.
    """

    return (
        get_approved_businesses()
        .filter(category=category)
    )