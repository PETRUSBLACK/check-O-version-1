"""
A shop's life before it starts trading: created, filled in, submitted, approved.

Check-O looks at every shop before shoppers can see it. That is a deliberate
choice, not a limitation: there is no dispute process yet, so the only thing
between a bad shop and Check-O's name is a person reading the form.

The waiting is never dead time. A draft shop can add products, upload photos and
set prices — all of it. It simply does not appear in anyone's search results
until someone has looked at it.

    draft ──submit──▶ pending ──approve──▶ approved   (shoppers can see it)
      ▲                  │
      └──── reject ───────┘  with a reason the vendor can read and fix
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.businesses.models import Business
from apps.businesses.choices import (
    BusinessCategory,
    BusinessStatus,
)

logger = logging.getLogger(__name__)


class BusinessFlowError(Exception):
    pass


def register_business(
    *,
    owner,
    name: str,
    slug: str = "",
    category: str = BusinessCategory.RETAIL,
    legal_name: str = "",
    registration_number: str = "",
    business_phone: str = "",
    address: str = "",
) -> Business:
    """
    Create a shop in draft.

    `slug` may be left out — Business.save() builds one from the name and makes
    it unique, so nobody has to invent a web address for their shop.

    Note there is no `tax_identifier` here: that lives on BusinessVerification,
    not on Business. Passing it used to raise TypeError the moment a vendor
    signed up with shop details attached.
    """
    with transaction.atomic():
        return Business.objects.create(
            owner=owner,
            name=name,
            slug=slug,
            category=category,
            status=BusinessStatus.DRAFT,
            legal_name=legal_name,
            registration_number=registration_number,
            business_phone=business_phone,
            address=address,
        )


def missing_before_review(business) -> list[str]:
    """
    What this shop still has to tell us before a human can usefully review it,
    phrased for the vendor rather than for the database.

    The app shows this list on the My shop screen, so a vendor always knows what
    is standing between them and going live. Returning [] means ready.
    """
    location = getattr(business, "location", None)
    has_address = bool((business.address or "").strip()) or bool(
        location is not None and (location.address or "").strip()
    )

    missing = []

    if not (business.business_phone or "").strip():
        missing.append("A phone number customers can reach you on")

    if not has_address:
        missing.append("The address of your shop")

    if location is None:
        # Without this the shop can never turn up in "shops near me", which is
        # the whole reason a customer opens Check-O rather than walking.
        missing.append("Where your shop is on the map, so nearby customers find you")

    if not business.products.filter(is_active=True).exists():
        missing.append("At least one product for sale")

    return missing


@transaction.atomic
def submit_business_for_review(*, business_id) -> Business:
    business = Business.objects.select_for_update().get(pk=business_id)

    if business.status not in (BusinessStatus.DRAFT, BusinessStatus.REJECTED):
        raise BusinessFlowError(
            "Only draft or rejected businesses can be submitted for review."
        )

    outstanding = missing_before_review(business)
    if outstanding:
        raise BusinessFlowError(
            "Your shop is not ready yet. Still needed: "
            + "; ".join(outstanding)
            + "."
        )

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

    _tell_the_reviewers(business)
    return business


@transaction.atomic
def approve_business(*, business_id) -> Business:
    business = Business.objects.select_for_update().get(pk=business_id)

    if business.status == BusinessStatus.APPROVED:
        raise BusinessFlowError("This shop is already approved.")

    if business.status != BusinessStatus.PENDING:
        raise BusinessFlowError(
            "Only a shop that has been submitted for review can be approved."
        )

    business.status = BusinessStatus.APPROVED
    business.verified_at = timezone.now()
    business.rejection_reason = ""
    business.save(
        update_fields=["status", "verified_at", "rejection_reason", "updated_at"]
    )

    _tell_the_owner(
        business,
        title=f"{business.name} is open on Check-O",
        body=(
            "Your shop has been approved. Customers near you can see it and your "
            "products now. Keep your stock up to date and you will not sell "
            "something you do not have."
        ),
        event_type="business.approved",
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

    # The reason goes in the message itself. A vendor who is only told "rejected"
    # has nothing to act on, and will either give up or submit the same thing again.
    _tell_the_owner(
        business,
        title=f"{business.name} needs a change before it goes live",
        body=f"{business.rejection_reason}\n\nFix that and submit your shop again.",
        event_type="business.rejected",
    )
    return business


def set_business_status(*, business_id, status: BusinessStatus) -> Business:
    """Legacy helper — prefer approve_business / reject_business."""
    business = Business.objects.select_for_update().get(pk=business_id)
    business.status = status
    business.save(update_fields=["status", "updated_at"])
    return business


# ─── Telling people ──────────────────────────────────────────────────────────
#
# Every one of these is wrapped: a shop must still get approved even if the
# message cannot be delivered. Silence is a nuisance; a failed approval is a
# vendor locked out of their own shop.


def _tell_the_owner(business, *, title: str, body: str, event_type: str) -> None:
    from apps.notifications.services.notification_service import notify

    try:
        notify(
            user=business.owner,
            title=title,
            body=body,
            event_type=event_type,
            payload={"business_id": str(business.pk), "status": business.status},
        )
    except Exception as exc:
        logger.error(
            "business_notify_failed business=%s event=%s error=%s",
            business.pk,
            event_type,
            exc,
        )


def _tell_the_reviewers(business) -> None:
    """
    A shop submitted and nobody told is a shop that waits a week. Message
    everyone who can actually approve it.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    from apps.notifications.services.notification_service import notify

    User = get_user_model()
    reviewers = User.objects.filter(
        Q(is_staff=True) | Q(role="admin"), is_active=True
    ).distinct()

    for reviewer in reviewers:
        try:
            notify(
                user=reviewer,
                title="A shop is waiting for review",
                body=(
                    f"{business.name} ({business.get_category_display()}) was "
                    f"submitted by {business.owner.email}. "
                    "Approve or reject it in the admin."
                ),
                event_type="business.submitted",
                payload={"business_id": str(business.pk)},
            )
        except Exception as exc:
            logger.error(
                "business_submit_notify_failed business=%s reviewer=%s error=%s",
                business.pk,
                reviewer.pk,
                exc,
            )
