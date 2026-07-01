"""
Business model.

Represents a registered business on the Check-O platform.

A Business is the core entity that owns branches, products,
employees, ratings, and other business resources.

Examples:
    - Shoprite
    - Chicken Republic
    - HealthPlus Pharmacy
    - Slot Nigeria
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from core.models import UUIDTimeStampedModel
from businesses.choices import BusinessCategory, BusinessStatus


class Business(UUIDTimeStampedModel):
    """
    Core business entity.

    Stores only the identity and public information of a business.

    Verification, documents, branches, staff, delivery zones,
    ratings, etc. are stored in their own models.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="businesses",
        help_text="Business owner.",
    )

    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Business display name.",
    )

    slug = models.SlugField(
        unique=True,
        max_length=255,
        blank=True,
        help_text="SEO-friendly unique identifier.",
    )

    category = models.CharField(
        max_length=50,
        choices=BusinessCategory.choices,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
        help_text="Business description.",
    )

    logo = models.ImageField(
        upload_to="businesses/logos/",
        null=True,
        blank=True,
    )

    cover_image = models.ImageField(
        upload_to="businesses/covers/",
        null=True,
        blank=True,
    )

    business_email = models.EmailField(
        blank=True,
    )

    business_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=BusinessStatus.choices,
        default=BusinessStatus.DRAFT,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Soft disable a business without deleting it.",
    )

    class Meta:
        db_table = "businesses_business"
        verbose_name = "Business"
        verbose_name_plural = "Businesses"

        ordering = [
            "name",
        ]

        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["category"]),
            models.Index(fields=["status"]),
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Automatically generate a unique slug.
        """
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Business.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    @property
    def is_restaurant(self):
        return self.category == BusinessCategory.RESTAURANT

    @property
    def is_supermarket(self):
        return self.category == BusinessCategory.GROCERY

    @property
    def is_pharmacy(self):
        return self.category == BusinessCategory.PHARMACY

    @property
    def is_retail_store(self):
        return self.category == BusinessCategory.RETAIL