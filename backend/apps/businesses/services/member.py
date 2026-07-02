from django.db import transaction

from apps.businesses.models import BusinessMember


@transaction.atomic
def add_business_member(
    *,
    business,
    user,
    role,
    branch=None,
    invited_by=None,
):
    """
    Adds a user to a business.
    """

    member, _ = BusinessMember.objects.get_or_create(
        business=business,
        user=user,
        defaults={
            "role": role,
            "branch": branch,
            "invited_by": invited_by,
        },
    )

    return member


@transaction.atomic
def remove_business_member(member):
    """
    Removes a business member.
    """

    member.delete()