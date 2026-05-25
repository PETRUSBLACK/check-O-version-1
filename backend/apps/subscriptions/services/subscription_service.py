"""
Subscription service.
Handles plan activation, renewal, cancellation, and enforcement of plan limits.
"""

import logging
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.subscriptions.models import SubscriptionPlan, SubscriptionStatus, VendorSubscription

logger = logging.getLogger(__name__)


class SubscriptionError(Exception):
    pass


@transaction.atomic
def subscribe(*, business, plan_id: UUID) -> VendorSubscription:
    """
    Subscribe a business to a plan.
    - Cancels any existing active subscription first.
    - Creates a new subscription starting immediately.
    - Free plans are activated instantly with no payment needed.
    - Paid plans are set to PENDING until payment is confirmed.
    """
    plan = SubscriptionPlan.objects.filter(pk=plan_id, is_active=True).first()
    if not plan:
        raise SubscriptionError("Subscription plan not found or inactive.")

    # Cancel existing active subscription
    existing = VendorSubscription.objects.filter(
        business=business,
        status=SubscriptionStatus.ACTIVE,
    ).first()
    if existing:
        _cancel_subscription(existing)

    now = timezone.now()
    expires_at = now + timezone.timedelta(days=30)

    # Free plans activate immediately
    if plan.price_monthly == 0:
        sub = VendorSubscription.objects.create(
            business=business,
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            expires_at=expires_at,
        )
        logger.info("subscription_activated_free business=%s plan=%s", business.pk, plan.slug)
    else:
        sub = VendorSubscription.objects.create(
            business=business,
            plan=plan,
            status=SubscriptionStatus.PENDING,
            started_at=None,
            expires_at=None,
        )
        logger.info("subscription_pending_payment business=%s plan=%s", business.pk, plan.slug)

    return sub


@transaction.atomic
def activate_subscription(*, subscription_id: UUID) -> VendorSubscription:
    """
    Activate a pending subscription after payment is confirmed.
    Called by payment confirmation flow.
    """
    sub = VendorSubscription.objects.select_for_update().get(pk=subscription_id)

    if sub.status == SubscriptionStatus.ACTIVE:
        return sub

    if sub.status != SubscriptionStatus.PENDING:
        raise SubscriptionError(f"Cannot activate subscription in status '{sub.status}'.")

    now = timezone.now()
    sub.status = SubscriptionStatus.ACTIVE
    sub.started_at = now
    sub.expires_at = now + timezone.timedelta(days=30)
    sub.save(update_fields=["status", "started_at", "expires_at", "updated_at"])

    # Notify vendor
    try:
        from apps.notifications.services.notification_service import notify
        notify(
            user=sub.business.owner,
            title="Subscription Activated",
            body=f"Your {sub.plan.name} plan is now active. Enjoy your benefits!",
            event_type="subscription.activated",
            payload={"plan": sub.plan.name, "expires_at": sub.expires_at.isoformat()},
        )
    except Exception:
        pass

    logger.info("subscription_activated id=%s business=%s plan=%s", sub.pk, sub.business_id, sub.plan.slug)
    return sub


@transaction.atomic
def renew_subscription(*, subscription_id: UUID) -> VendorSubscription:
    """
    Renew an active or expired subscription by 30 days.
    Called by auto-renewal background task.
    """
    sub = VendorSubscription.objects.select_for_update().get(pk=subscription_id)

    if not sub.auto_renew:
        raise SubscriptionError("Auto-renewal is disabled for this subscription.")

    now = timezone.now()
    # Extend from expiry date or now (whichever is later)
    base = max(sub.expires_at, now) if sub.expires_at else now
    sub.expires_at = base + timezone.timedelta(days=30)
    sub.status = SubscriptionStatus.ACTIVE
    sub.save(update_fields=["status", "expires_at", "updated_at"])

    logger.info("subscription_renewed id=%s business=%s new_expiry=%s", sub.pk, sub.business_id, sub.expires_at)
    return sub


@transaction.atomic
def cancel_subscription(*, subscription_id: UUID) -> VendorSubscription:
    """Cancel a subscription. Remains active until expiry date."""
    sub = VendorSubscription.objects.select_for_update().get(pk=subscription_id)
    return _cancel_subscription(sub)


def _cancel_subscription(sub: VendorSubscription) -> VendorSubscription:
    sub.status = SubscriptionStatus.CANCELLED
    sub.cancelled_at = timezone.now()
    sub.auto_renew = False
    sub.save(update_fields=["status", "cancelled_at", "auto_renew", "updated_at"])

    try:
        from apps.notifications.services.notification_service import notify
        notify(
            user=sub.business.owner,
            title="Subscription Cancelled",
            body=f"Your {sub.plan.name} plan has been cancelled. Access continues until {sub.expires_at.strftime('%d %b %Y') if sub.expires_at else 'end of billing period'}.",
            event_type="subscription.cancelled",
            payload={"plan": sub.plan.name},
        )
    except Exception:
        pass

    logger.info("subscription_cancelled id=%s business=%s", sub.pk, sub.business_id)
    return sub


def get_active_subscription(*, business) -> VendorSubscription | None:
    """Get the current active subscription for a business."""
    return VendorSubscription.objects.filter(
        business=business,
        status=SubscriptionStatus.ACTIVE,
        expires_at__gt=timezone.now(),
    ).select_related("plan").first()


def enforce_product_limit(*, business) -> None:
    """
    Check if the business can add more products based on their plan.
    Raises SubscriptionError if limit is reached.
    """
    sub = get_active_subscription(business=business)
    plan = sub.plan if sub else _get_free_plan()
    if plan is None:
        return

    current_count = business.products.filter(is_active=True).count()
    if current_count >= plan.max_products:
        raise SubscriptionError(
            f"Your {plan.name} plan allows a maximum of {plan.max_products} active products. "
            f"Upgrade your plan to list more products."
        )


def enforce_promotion_limit(*, business) -> None:
    """
    Check if the business can run more promotions based on their plan.
    Raises SubscriptionError if limit is reached.
    """
    from django.utils import timezone as tz
    sub = get_active_subscription(business=business)
    plan = sub.plan if sub else _get_free_plan()
    if plan is None:
        return

    from apps.ads.models import ProductPromotion
    active_promotions = ProductPromotion.objects.filter(
        product__business=business,
        is_active=True,
        ends_at__gt=tz.now(),
    ).count()

    if active_promotions >= plan.max_promotions:
        raise SubscriptionError(
            f"Your {plan.name} plan allows a maximum of {plan.max_promotions} active promotion(s). "
            f"Upgrade your plan to run more promotions."
        )


def _get_free_plan() -> SubscriptionPlan | None:
    return SubscriptionPlan.objects.filter(price_monthly=0, is_active=True).first()
