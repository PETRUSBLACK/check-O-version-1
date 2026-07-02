from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.businesses.models import (
    Business,
    Branch,
    BusinessMember,
)

from apps.businesses.choices import BusinessMemberRole


@receiver(post_save, sender=Business)
def create_default_business_resources(sender, instance, created, **kwargs):
    """
    Automatically create:

    - Main Branch
    - Owner membership
    """

    if not created:
        return

    Branch.objects.create(
        business=instance,
        name="Main Branch",
    )

    BusinessMember.objects.create(
        business=instance,
        user=instance.owner,
        role=BusinessMemberRole.OWNER,
    )