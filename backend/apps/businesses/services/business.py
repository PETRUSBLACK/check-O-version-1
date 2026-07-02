from django.db import transaction

from apps.businesses.models import Business


@transaction.atomic
def create_business(*, owner, **validated_data):
    """
    Creates a new business.

    Signals automatically create:
        - Main Branch
        - Owner Membership
    """

    business = Business.objects.create(
        owner=owner,
        **validated_data,
    )

    return business


@transaction.atomic
def update_business(*, business, **validated_data):
    """
    Updates a business.
    """

    for field, value in validated_data.items():
        setattr(business, field, value)

    business.save()

    return business