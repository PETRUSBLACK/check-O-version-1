from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessStatus
from apps.subscriptions.models import SubscriptionPlan, SubscriptionStatus, VendorSubscription, PlanTier
from apps.subscriptions.services.subscription_service import (
    subscribe, activate_subscription, cancel_subscription,
    enforce_product_limit, get_active_subscription, SubscriptionError,
)
from apps.ads.models import ProductPromotion, PromotionType
from apps.ads.services.promotion_service import create_promotion, PromotionError
from apps.products.models import Product
from apps.users.models import User, UserRole


def make_user(email, role=UserRole.CUSTOMER, password="testpass12345"):
    return User.objects.create_user(email=email, password=password, role=role)


def make_vendor(email="vendor@example.com"):
    return make_user(email, role=UserRole.VENDOR)


def make_business(owner, slug="test-shop"):
    return Business.objects.create(
        owner=owner, name="Test Shop", slug=slug,
        legal_name="Test Ltd", registration_number="RC1234567",
        status=BusinessStatus.APPROVED,
    )


def make_plan(name="Starter", price="5000.00", tier=PlanTier.STARTER, max_products=50, max_promotions=3):
    return SubscriptionPlan.objects.create(
        name=name, slug=name.lower(),
        tier=tier, price_monthly=price,
        max_products=max_products, max_promotions=max_promotions,
        is_active=True,
    )


def make_free_plan():
    return SubscriptionPlan.objects.create(
        name="Free", slug="free", tier=PlanTier.FREE,
        price_monthly="0.00", max_products=10, max_promotions=1,
        is_active=True,
    )


def make_product(business, name="Widget", stock=10):
    return Product.objects.create(
        business=business, name=name, price="100.00", stock=stock, is_active=True,
    )


class SubscriptionServiceTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)

    def test_free_plan_activates_immediately(self):
        plan = make_free_plan()
        sub = subscribe(business=self.business, plan_id=plan.pk)
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)
        self.assertIsNotNone(sub.expires_at)

    def test_paid_plan_starts_as_pending(self):
        plan = make_plan()
        sub = subscribe(business=self.business, plan_id=plan.pk)
        self.assertEqual(sub.status, SubscriptionStatus.PENDING)

    def test_activate_pending_subscription(self):
        plan = make_plan()
        sub = subscribe(business=self.business, plan_id=plan.pk)
        self.assertEqual(sub.status, SubscriptionStatus.PENDING)
        activated = activate_subscription(subscription_id=sub.pk)
        self.assertEqual(activated.status, SubscriptionStatus.ACTIVE)
        self.assertIsNotNone(activated.started_at)
        self.assertIsNotNone(activated.expires_at)

    def test_cancel_subscription(self):
        plan = make_free_plan()
        sub = subscribe(business=self.business, plan_id=plan.pk)
        cancelled = cancel_subscription(subscription_id=sub.pk)
        self.assertEqual(cancelled.status, SubscriptionStatus.CANCELLED)
        self.assertFalse(cancelled.auto_renew)
        self.assertIsNotNone(cancelled.cancelled_at)

    def test_subscribing_again_cancels_existing(self):
        plan1 = make_free_plan()
        plan2 = make_plan(name="Growth", price="10000.00", tier=PlanTier.GROWTH)
        sub1 = subscribe(business=self.business, plan_id=plan1.pk)
        sub2 = subscribe(business=self.business, plan_id=plan2.pk)
        sub1.refresh_from_db()
        self.assertEqual(sub1.status, SubscriptionStatus.CANCELLED)

    def test_get_active_subscription(self):
        plan = make_free_plan()
        subscribe(business=self.business, plan_id=plan.pk)
        active = get_active_subscription(business=self.business)
        self.assertIsNotNone(active)
        self.assertEqual(active.plan.slug, "free")

    def test_product_limit_enforcement(self):
        plan = SubscriptionPlan.objects.create(
            name="Tiny", slug="tiny", tier=PlanTier.FREE,
            price_monthly="0.00", max_products=2, max_promotions=1, is_active=True,
        )
        sub = subscribe(business=self.business, plan_id=plan.pk)
        make_product(self.business, name="P1")
        make_product(self.business, name="P2")
        with self.assertRaises(SubscriptionError):
            enforce_product_limit(business=self.business)

    def test_inactive_plan_cannot_be_subscribed(self):
        plan = make_plan(name="Inactive")
        plan.is_active = False
        plan.save()
        with self.assertRaises(SubscriptionError):
            subscribe(business=self.business, plan_id=plan.pk)


class SubscriptionAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.plan = make_free_plan()

    def test_plans_are_publicly_listed(self):
        res = self.client.get("/api/subscription-plans/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data["results"]), 1)

    def test_vendor_can_subscribe(self):
        self.client.force_authenticate(self.vendor)
        res = self.client.post("/api/subscriptions/subscribe/", {
            "business_id": str(self.business.pk),
            "plan_id": str(self.plan.pk),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["status"], SubscriptionStatus.ACTIVE)

    def test_vendor_can_cancel_subscription(self):
        self.client.force_authenticate(self.vendor)
        self.client.post("/api/subscriptions/subscribe/", {
            "business_id": str(self.business.pk),
            "plan_id": str(self.plan.pk),
        }, format="json")
        sub = VendorSubscription.objects.filter(business=self.business).first()
        res = self.client.post(f"/api/subscriptions/{sub.pk}/cancel/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], SubscriptionStatus.CANCELLED)

    def test_active_subscription_endpoint(self):
        subscribe(business=self.business, plan_id=self.plan.pk)
        self.client.force_authenticate(self.vendor)
        res = self.client.get(f"/api/businesses/{self.business.pk}/subscription/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class PromotionServiceTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.product = make_product(self.business)
        self.plan = make_plan(max_promotions=3)
        subscribe(business=self.business, plan_id=self.plan.pk)
        sub = VendorSubscription.objects.filter(business=self.business).first()
        activate_subscription(subscription_id=sub.pk)

    def _future_dates(self, days_from_now=1, duration_days=7):
        now = timezone.now()
        return now + timezone.timedelta(days=days_from_now), now + timezone.timedelta(days=days_from_now + duration_days)

    def test_create_featured_promotion(self):
        starts, ends = self._future_dates()
        promo = create_promotion(
            product=self.product, title="Featured Widget",
            promotion_type=PromotionType.FEATURED,
            starts_at=starts, ends_at=ends, boost_weight=5,
        )
        self.assertIsNotNone(promo.pk)
        self.assertEqual(promo.promotion_type, PromotionType.FEATURED)

    def test_create_discount_promotion(self):
        starts, ends = self._future_dates()
        promo = create_promotion(
            product=self.product, title="10% Off",
            promotion_type=PromotionType.DISCOUNT,
            starts_at=starts, ends_at=ends,
            discount_percent=Decimal("10.00"),
        )
        self.assertEqual(promo.discount_percent, Decimal("10.00"))
        self.assertEqual(promo.discounted_price, Decimal("90.00"))

    def test_discount_without_percent_raises_error(self):
        starts, ends = self._future_dates()
        with self.assertRaises(PromotionError):
            create_promotion(
                product=self.product, title="Bad Discount",
                promotion_type=PromotionType.DISCOUNT,
                starts_at=starts, ends_at=ends,
                discount_percent=Decimal("0"),
            )

    def test_past_end_date_raises_error(self):
        past = timezone.now() - timezone.timedelta(days=1)
        with self.assertRaises(PromotionError):
            create_promotion(
                product=self.product, title="Expired",
                promotion_type=PromotionType.FEATURED,
                starts_at=timezone.now() - timezone.timedelta(days=2),
                ends_at=past,
            )

    def test_promotion_limit_enforced(self):
        plan = SubscriptionPlan.objects.create(
            name="Limited", slug="limited", tier=PlanTier.FREE,
            price_monthly="0.00", max_products=50, max_promotions=1, is_active=True,
        )
        sub = subscribe(business=self.business, plan_id=plan.pk)
        activate_subscription(subscription_id=sub.pk)
        starts, ends = self._future_dates()
        create_promotion(
            product=self.product, title="First",
            promotion_type=PromotionType.FEATURED,
            starts_at=starts, ends_at=ends,
        )
        with self.assertRaises(PromotionError):
            create_promotion(
                product=self.product, title="Second",
                promotion_type=PromotionType.FEATURED,
                starts_at=starts, ends_at=ends,
            )


class PromotionAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.product = make_product(self.business)
        plan = make_plan()
        sub = subscribe(business=self.business, plan_id=plan.pk)
        activate_subscription(subscription_id=sub.pk)

    def test_featured_products_endpoint(self):
        res = self.client.get("/api/promotions/featured/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_discounts_endpoint(self):
        res = self.client.get("/api/promotions/discounts/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_vendor_can_create_promotion(self):
        self.client.force_authenticate(self.vendor)
        starts = (timezone.now() + timezone.timedelta(days=1)).isoformat()
        ends = (timezone.now() + timezone.timedelta(days=8)).isoformat()
        res = self.client.post("/api/promotions/", {
            "product": str(self.product.pk),
            "title": "Featured Widget",
            "promotion_type": "featured",
            "starts_at": starts,
            "ends_at": ends,
            "boost_weight": 3,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_customer_cannot_create_promotion(self):
        customer = make_user("cust@example.com")
        self.client.force_authenticate(customer)
        res = self.client.post("/api/promotions/", {
            "product": str(self.product.pk), "title": "X",
            "starts_at": timezone.now().isoformat(),
            "ends_at": timezone.now().isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
