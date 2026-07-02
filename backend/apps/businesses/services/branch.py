from django.db import transaction

from apps.businesses.models import Branch


@transaction.atomic
def create_branch(*, business, **validated_data):
    """
    Creates a branch for a business.
    """

    return Branch.objects.create(
        business=business,
        **validated_data,
    )


@transaction.atomic
def update_branch(*, branch, **validated_data):
    """
    Updates a branch.
    """

    for field, value in validated_data.items():
        setattr(branch, field, value)

    branch.save()

    return branch