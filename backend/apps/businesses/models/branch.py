"""
Branch model.

Represents a physical location of a business.

Examples:

Shoprite
    ├── Lekki Branch
    ├── Ikeja Branch
    └── Abuja Branch
"""

import uuid

from django.db import models
from django.utils.text import slugify

from core.models import UUIDTimeStampedModel

from .business import Business


class Branch(UUIDTimeStampedModel):
    """
    Physical location of a business.

    Inventory, staff, orders, operating hours,
    delivery zones and reservations belong to a branch.
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="branches",
        help_text="Business that owns this branch.",
    )

    name = models.CharField(
        max_length=255,
        help_text="Example: Lekki Branch",
    )

    slug = models.SlugField(
        unique=True,
        blank=True,
        max_length=255,
        help_text="SEO-friendly unique branch identifier.",
    )

    branch_code = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        help_text="Automatically generated unique branch code.",
    )

    email = models.EmailField(
        blank=True,
        help_text="Branch contact email.",
    )

    phone_number = models.CharField(
        max_length=30,
        blank=True,
        help_text="Branch contact phone number.",
    )

    manager_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Branch manager's full name.",
    )

    full_address = models.TextField(
        help_text="Complete physical address.",
    )

    city = models.CharField(
        max_length=100,
        db_index=True,
    )

    state = models.CharField(
        max_length=100,
        db_index=True,
    )

    country = models.CharField(
        max_length=100,
        default="Nigeria",
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    timezone = models.CharField(
        max_length=50,
        default="Africa/Lagos",
        help_text="Branch timezone.",
    )

    opening_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the branch commenced operations.",
    )

    display_order = models.PositiveIntegerField(
        default=1,
        help_text="Display ordering for multiple branches.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Soft disable the branch.",
    )

    accepts_walk_in = models.BooleanField(
        default=True,
        help_text="Whether customers can visit without reservations.",
    )

    supports_delivery = models.BooleanField(
        default=True,
        help_text="Whether delivery is available.",
    )

    supports_pickup = models.BooleanField(
        default=True,
        help_text="Whether customer pickup is available.",
    )

    class Meta:
        db_table = "businesses_branch"
        verbose_name = "Branch"
        verbose_name_plural = "Branches"

        ordering = [
            "business",
            "display_order",
            "name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["business", "name"],
                name="unique_branch_name_per_business",
            )
        ]

        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["city"]),
            models.Index(fields=["state"]),
            models.Index(fields=["country"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.business.name} - {self.name}"

    def save(self, *args, **kwargs):
        """
        Automatically generate slug and branch code.
        """

        if not self.slug:
            base_slug = slugify(f"{self.business.name}-{self.name}")
            slug = base_slug
            counter = 1

            while Branch.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        if not self.branch_code:
            self.branch_code = f"BR-{uuid.uuid4().hex[:8].upper()}"

        super().save(*args, **kwargs)

    @property
    def full_location(self):
        """
        Human-readable location.
        """
        return f"{self.city}, {self.state}, {self.country}"

    @property
    def coordinates(self):
        """
        Latitude and longitude tuple.
        """
        return (
            float(self.latitude),
            float(self.longitude),
        )