from django.db import transaction
from django.utils import timezone

from apps.businesses.choices import (
    BusinessStatus,
    VerificationStatus,
)


@transaction.atomic
def submit_business_for_verification(verification):
    """
    Submit a business for review.
    """

    verification.status = VerificationStatus.PENDING
    verification.submitted_at = timezone.now()
    verification.save()

    business = verification.business
    business.status = BusinessStatus.PENDING
    business.save()

    return verification


@transaction.atomic
def approve_business_verification(*, verification, admin_user):
    """
    Approves verification.
    """

    verification.status = VerificationStatus.APPROVED
    verification.verified_at = timezone.now()
    verification.verified_by = admin_user
    verification.save()

    business = verification.business
    business.status = BusinessStatus.APPROVED
    business.save()

    return verification


@transaction.atomic
def reject_business_verification(
    *,
    verification,
    admin_user,
    reason,
):
    """
    Rejects verification.
    """

    verification.status = VerificationStatus.REJECTED
    verification.verified_by = admin_user
    verification.rejection_reason = reason
    verification.save()

    business = verification.business
    business.status = BusinessStatus.REJECTED
    business.save()

    return verification