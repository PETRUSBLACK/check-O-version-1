from django.shortcuts import get_object_or_404

from apps.businesses.models import Business


def get_business_by_id(pk):
    """
    Returns a business by UUID.
    """

    return get_object_or_404(
        Business.objects.select_related("owner"),
        pk=pk,
    )


def get_business_by_slug(slug):
    """
    Returns a business using its slug.
    """

    return get_object_or_404(
        Business.objects.select_related("owner"),
        slug=slug,
    )


def get_user_businesses(user):
    """
    Businesses owned by a user.
    """

    return (
        Business.objects
        .filter(
            owner=user,
            is_active=True,
        )
        .order_by("name")
    )


def get_all_active_businesses():
    """
    Public businesses.
    """

    return (
        Business.objects
        .filter(
            is_active=True,
        )
        .select_related("owner")
        .order_by("name")
    )