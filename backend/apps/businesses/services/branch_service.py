"""
Branch services.
"""

from apps.businesses.models import Branch


def create_branch(**data):
    """
    Create a new branch.
    """

    return Branch.objects.create(**data)


def update_branch(branch, **data):
    """
    Update a branch.
    """

    for attr, value in data.items():
        setattr(branch, attr, value)

    branch.save()

    return branch