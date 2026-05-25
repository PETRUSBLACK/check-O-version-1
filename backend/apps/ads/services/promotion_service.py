"""
Promotions / Ads service.
Handles creation, validation, featured listings, and impression/click tracking.
"""

import logging
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.ads.models import ProductPromotion, PromotionType
from apps.subscriptions.services.subscription_service import SubscriptionError, enforce_promotion_limit

logger = logging.getLogger(__name__)


class PromotionError(Exception):
    pass


@transaction.atomic
def create_promotion(
    *,
    product,
    title: str,
    promotion_type: str,
    starts_at,
    ends_at,
    boost_weight: int = 1,
    discount_percent: Decimal = Decimal("0"),
    budget: Decimal = Decimal("0"),
) -> ProductPromotion:
    """
    Create a product promotion.
    - Validates date range.
    - Enforces subscription plan promotion limits.
    - Discount promotions require a discount_percent > 0.
    """
    if ends_at <= starts_at:
        raise PromotionError("End date must be after start date.")

    if ends_at <= timezone.now():
        raise PromotionError("End date must be in the future.")

    if promotion_type in (PromotionType.DISCOUNT, PromotionType.FLASH_SALE):
        if discount_percent <= 0 or discount_percent > 90:
            raise PromotionError("Discount must be between 1% and 90%.")

    # Enforce subscription limit
    try:
        enforce_promotion_limit(business=product.business)
    except SubscriptionError as exc:
        raise PromotionError(str(exc)) from exc

    promotion = ProductPromotion.objects.create(
        product=product,
        title=title,
        promotion_type=promotion_type,
        boost_weight=boost_weight,
        discount_percent=discount_percent,
        starts_at=starts_at,
        ends_at=ends_at,
        budget=budget,
        is_active=True,
    )

    logger.info(
        "promotion_created id=%s product=%s type=%s",
        promotion.pk, product.pk, promotion_type,
    )
    return promotion


@transaction.atomic
def deactivate_promotion(*, promotion_id: UUID) -> ProductPromotion:
    """Deactivate a promotion before its end date."""
    promotion = ProductPromotion.objects.select_for_update().get(pk=promotion_id)
    promotion.is_active = False
    promotion.save(update_fields=["is_active", "updated_at"])
    logger.info("promotion_deactivated id=%s", promotion_id)
    return promotion


def record_impression(*, promotion_id: UUID) -> None:
    """Increment impression count. Called when promotion is displayed."""
    ProductPromotion.objects.filter(pk=promotion_id).update(
        impressions=models_F("impressions") + 1
    )


def record_click(*, promotion_id: UUID) -> None:
    """Increment click count. Called when promotion is clicked."""
    ProductPromotion.objects.filter(pk=promotion_id).update(
        clicks=models_F("clicks") + 1
    )


def get_featured_products(*, limit: int = 20, city: str = "") -> list:
    """
    Get featured/promoted products for homepage or search results.
    Ordered by boost_weight descending.
    Optionally filtered by city for location-aware featuring.
    """
    now = timezone.now()
    qs = ProductPromotion.objects.filter(
        is_active=True,
        starts_at__lte=now,
        ends_at__gte=now,
        product__is_active=True,
        product__business__status="approved",
    ).select_related(
        "product__business__location",
    ).order_by("-boost_weight", "-created_at")

    if city:
        qs = qs.filter(product__business__location__city__icontains=city)

    return list(qs[:limit])


def get_active_discounts(*, business=None) -> list:
    """Get all active discount/flash sale promotions, optionally for a specific business."""
    now = timezone.now()
    qs = ProductPromotion.objects.filter(
        is_active=True,
        starts_at__lte=now,
        ends_at__gte=now,
        promotion_type__in=[PromotionType.DISCOUNT, PromotionType.FLASH_SALE],
        discount_percent__gt=0,
    ).select_related("product")

    if business:
        qs = qs.filter(product__business=business)

    return list(qs.order_by("-discount_percent"))


# Django F() import
from django.db.models import F as models_F
