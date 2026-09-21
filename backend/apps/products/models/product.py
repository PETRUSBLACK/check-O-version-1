"""
Enterprise Product model for SmartMall.

This model represents products sold by vendors on the SmartMall platform.

Features
--------
- Business ownership
- Product category
- SKU & Barcode
- Automatic slug generation
- Automatic SKU generation
- Multi-currency support
- SmartMall channel allocation
- Inventory management
- Low-stock alerts
- Featured products
- Published/Draft workflow
"""

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from core.models import UUIDTimeStampedModel

from apps.businesses.models import Business
from .category import ProductCategory


class Product(UUIDTimeStampedModel):
    """
    Main Product model.
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="products",
    )

    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        unique=True,
        db_index=True,
        null=True,
        blank=True,
    )

    sku = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text="Stock Keeping Unit",
    )

    barcode = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        default="NGN",
        help_text="ISO Currency Code",
    )

    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    stock = models.PositiveIntegerField(
        default=0,
    )

    smartmall_allocation = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Units reserved exclusively for SmartMall.",
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=5,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_featured = models.BooleanField(
        default=False,
    )

    is_published = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "products_product"

        ordering = [
            "name",
        ]

        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["category"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["barcode"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["is_published"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.business.name})"

    @property
    def uses_channel_allocation(self):
        """
        Returns True if SmartMall stock allocation is enabled.
        """
        return self.smartmall_allocation is not None

    @property
    def available_stock(self):
        """
        Available stock visible on SmartMall.
        """
        if self.smartmall_allocation is None:
            return self.stock

        return min(self.stock, self.smartmall_allocation)

    def generate_sku(self):
        """
        Generates a unique SKU.
        Example:
            SMP-8F42A7B1
        """
        while True:
            sku = f"SMP-{uuid.uuid4().hex[:8].upper()}"

            if not Product.objects.filter(sku=sku).exists():
                return sku

    def generate_slug(self):
        """
        Generates a unique slug.
        """
        base_slug = slugify(self.name)

        slug = base_slug

        counter = 1

        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def save(self, *args, **kwargs):
        """
        Auto-generate SKU and slug.
        """

        if not self.slug:
            self.slug = self.generate_slug()

        if not self.sku:
            self.sku = self.generate_sku()

        super().save(*args, **kwargs)