from django.db import models
from django.utils import timezone

from apps.products.models import Product
from core.models import UUIDTimeStampedModel


class PromotionType(models.TextChoices):
    FEATURED = "featured", "Featured Listing"
    DISCOUNT = "discount", "Discount"
    FLASH_SALE = "flash_sale", "Flash Sale"
    BANNER = "banner", "Banner Ad"


class ProductPromotion(UUIDTimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="promotions")
    title = models.CharField(max_length=255)
    promotion_type = models.CharField(max_length=20, choices=PromotionType.choices, default=PromotionType.FEATURED)
    boost_weight = models.PositiveSmallIntegerField(default=1, help_text="Higher = appears more prominently")
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Discount percentage (0 = no discount)"
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Ad spend budget in Naira")
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "ads_productpromotion"
        ordering = ["-boost_weight", "-starts_at"]

    def __str__(self):
        return f"{self.title} — {self.product.name}"

    @property
    def is_currently_active(self):
        now = timezone.now()
        return self.is_active and self.starts_at <= now <= self.ends_at

    @property
    def discounted_price(self):
        if self.discount_percent > 0:
            discount = self.product.price * (self.discount_percent / 100)
            return self.product.price - discount
        return self.product.price

    @property
    def ctr(self):
        """Click-through rate."""
        if self.impressions == 0:
            return 0
        return round((self.clicks / self.impressions) * 100, 2)
