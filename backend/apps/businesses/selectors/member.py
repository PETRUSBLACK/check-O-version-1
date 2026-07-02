from django.shortcuts import get_object_or_404

from apps.businesses.models import BusinessMember


def get_business_members(business):
    """
    Returns active members of a business.
    """

    return (
        BusinessMember.objects
        .filter(
            business=business,
            is_active=True,
        )
        .select_related(
            "user",
            "branch",
        )
        .order_by("role", "user__email")
    )


def get_business_member(pk):
    """
    Returns a single business member.
    """

    return get_object_or_404(
        BusinessMember.objects.select_related(
            "user",
            "business",
            "branch",
        ),
        pk=pk,
    )