"""
Business model.

Represents a registered business on the Check-O platform.
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from core.models import UUIDTimeStampedModel
from apps.businesses.choices import (
    BusinessCategory,
    BusinessStatus,
)


class Business(UUIDTimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="businesses",
    )

    name = models.CharField(
        max_length=255,
        db_index=True,
    )

    slug = models.SlugField(
        unique=True,
        blank=True,
        max_length=255,
    )

    category = models.CharField(
        max_length=50,
        choices=BusinessCategory.choices,
        db_index=True,
    )

    tagline = models.CharField(
        max_length=255,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    logo = models.ImageField(
        upload_to="businesses/logos/",
        blank=True,
        null=True,
    )

    cover_image = models.ImageField(
        upload_to="businesses/covers/",
        blank=True,
        null=True,
    )

    business_email = models.EmailField(
        blank=True,
        null=True,
    )

    business_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    website = models.URLField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=BusinessStatus.choices,
        default=BusinessStatus.DRAFT,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "businesses_business"
        verbose_name = "Business"
        verbose_name_plural = "Businesses"

        ordering = ["name"]

indexes = [
    models.Index(fields=["owner"]),
    models.Index(fields=["category"]),
    models.Index(fields=["status"]),
    models.Index(fields=["name"]),
    models.Index(fields=["created_at"]),
]
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
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
        return self.category == BusinessCategory.SUPERMARKET

    @property
    def is_pharmacy(self):
        return self.category == BusinessCategory.PHARMACY

    @property
    def is_retail_store(self):
        return self.category == BusinessCategory.RETAIL

    @property
    def is_approved(self):
        return self.status == BusinessStatus.APPROVED

    @property
    def is_pending(self):
        return self.status == BusinessStatus.PENDING

    @property
    def is_suspended(self):
        return self.status == BusinessStatus.SUSPENDED