from django.shortcuts import get_object_or_404

from apps.businesses.models import Branch


def get_branch_by_id(pk):
    """
    Returns a branch.
    """

    return get_object_or_404(
        Branch.objects.select_related("business"),
        pk=pk,
    )


def get_business_branches(business):
    """
    Returns active branches belonging to a business.
    """

    return (
        Branch.objects
        .filter(
            business=business,
            is_active=True,
        )
        .order_by("name")
    )