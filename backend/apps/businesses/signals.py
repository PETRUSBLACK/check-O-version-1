"""
Signals for the businesses app.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from businesses.models import (
    Business,
    Branch,
    BusinessMember,
)
from businesses.choices import BusinessMemberRole


@receiver(post_save, sender=Business)
def create_default_business_resources(sender, instance, created, **kwargs):
    """
    Automatically create:
        - Main Branch
        - Owner Membership
    """

    if not created:
        return

    Branch.objects.create(
        business=instance,
        name="Main Branch",
        city="",
        state="",
        full_address="",
        latitude=0,
        longitude=0,
    )

    BusinessMember.objects.create(
        business=instance,
        user=instance.owner,
        role=BusinessMemberRole.OWNER,
    )