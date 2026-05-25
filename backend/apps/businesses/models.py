from django.conf import settings
from django.db import models

from core.models import UUIDTimeStampedModel


class BusinessStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"


class Business(UUIDTimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="businesses",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    status = models.CharField(
        max_length=20,
        choices=BusinessStatus.choices,
        default=BusinessStatus.DRAFT,
    )
    legal_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Registered legal name for verification.",
    )
    registration_number = models.CharField(
        max_length=128,
        blank=True,
        help_text="Business / company registration number.",
    )
    tax_identifier = models.CharField(
        max_length=64,
        blank=True,
        help_text="Tax ID / VAT where applicable.",
    )
    business_phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    submitted_for_review_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "businesses_business"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class BusinessLocation(UUIDTimeStampedModel):
    """
    Physical location of a vendor's shop.
    Enables location-based product search.
    """
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="location",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Nigeria")
    full_address = models.TextField(blank=True)

    class Meta:
        db_table = "businesses_location"

    def __str__(self):
        return f"{self.business.name} — ({self.latitude}, {self.longitude})"


class BusinessRating(UUIDTimeStampedModel):
    """Customer rating for a vendor shop."""
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    customer = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="business_ratings",
    )
    score = models.PositiveSmallIntegerField()  # 1-5
    review = models.TextField(blank=True)

    class Meta:
        db_table = "businesses_rating"
        unique_together = ("business", "customer")

    def __str__(self):
        return f"{self.business.name} — {self.score}/5"
