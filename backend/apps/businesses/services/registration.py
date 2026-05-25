from django.db import transaction
from django.utils import timezone

from apps.businesses.models import Business, BusinessStatus


def register_business(
    *,
    owner,
    name: str,
    slug: str,
    legal_name: str = "",
    registration_number: str = "",
    tax_identifier: str = "",
    business_phone: str = "",
    address: str = "",
) -> Business:
    with transaction.atomic():
        return Business.objects.create(
            owner=owner,
            name=name,
            slug=slug,
            status=BusinessStatus.DRAFT,
            legal_name=legal_name,
            registration_number=registration_number,
            tax_identifier=tax_identifier,
            business_phone=business_phone,
            address=address,
        )


class BusinessFlowError(Exception):
    pass


@transaction.atomic
def submit_business_for_review(*, business_id) -> Business:
    business = Business.objects.select_for_update().get(pk=business_id)
    if business.status not in (BusinessStatus.DRAFT, BusinessStatus.REJECTED):
        raise BusinessFlowError(
            "Only draft or rejected businesses can be submitted for review."
        )
    missing = []
    if not business.legal_name.strip():
        missing.append("legal_name")
    if not business.registration_number.strip():
        missing.append("registration_number")
    if not business.address.strip():
        missing.append("address")
    if missing:
        raise BusinessFlowError(f"Missing required fields: {', '.join(missing)}")
    business.status = BusinessStatus.PENDING
    business.submitted_for_review_at = timezone.now()
    business.rejection_reason = ""
    business.save(
        update_fields=[
            "status",
            "submitted_for_review_at",
            "rejection_reason",
            "updated_at",
        ]
    )
    return business


@transaction.atomic
def approve_business(*, business_id) -> Business:
    business = Business.objects.select_for_update().get(pk=business_id)
    if business.status != BusinessStatus.PENDING:
        raise BusinessFlowError("Only pending businesses can be approved.")
    business.status = BusinessStatus.APPROVED
    business.verified_at = timezone.now()
    business.rejection_reason = ""
    business.save(
        update_fields=["status", "verified_at", "rejection_reason", "updated_at"]
    )
    return business


@transaction.atomic
def reject_business(*, business_id, reason: str) -> Business:
    business = Business.objects.select_for_update().get(pk=business_id)
    if business.status != BusinessStatus.PENDING:
        raise BusinessFlowError("Only pending businesses can be rejected.")
    if not reason or not str(reason).strip():
        raise BusinessFlowError("rejection_reason is required.")
    business.status = BusinessStatus.REJECTED
    business.rejection_reason = reason.strip()
    business.save(update_fields=["status", "rejection_reason", "updated_at"])
    return business


def set_business_status(*, business_id, status: BusinessStatus) -> Business:
    """Legacy helper — prefer approve_business / reject_business."""
    business = Business.objects.select_for_update().get(pk=business_id)
    business.status = status
    business.save(update_fields=["status", "updated_at"])
    return business
