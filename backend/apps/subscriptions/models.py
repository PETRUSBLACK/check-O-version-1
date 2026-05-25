from django.db import models
from django.utils import timezone

from apps.businesses.models import Business
from core.models import UUIDTimeStampedModel


class PlanTier(models.TextChoices):
    FREE = "free", "Free"
    STARTER = "starter", "Starter"
    GROWTH = "growth", "Growth"
    PRO = "pro", "Pro"


class SubscriptionPlan(UUIDTimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    tier = models.CharField(max_length=20, choices=PlanTier.choices, default=PlanTier.FREE)
    price_monthly = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_products = models.PositiveIntegerField(default=10, help_text="Max products vendor can list")
    max_promotions = models.PositiveIntegerField(default=1, help_text="Max active promotions allowed")
    featured_listing = models.BooleanField(default=False, help_text="Appear in featured section")
    analytics_access = models.BooleanField(default=False, help_text="Access to advanced analytics")
    priority_support = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscriptions_plan"
        ordering = ["price_monthly"]

    def __str__(self):
        return f"{self.name} (₦{self.price_monthly}/mo)"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"
    PENDING = "pending", "Pending Payment"


class VendorSubscription(UUIDTimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="vendor_subscriptions")
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subscriptions_vendorsubscription"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business.name} — {self.plan.name}"

    @property
    def is_active(self):
        return (
            self.status == SubscriptionStatus.ACTIVE
            and self.expires_at
            and timezone.now() < self.expires_at
        )

    @property
    def days_remaining(self):
        if not self.expires_at:
            return 0
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
