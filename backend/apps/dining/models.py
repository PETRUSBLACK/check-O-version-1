from django.conf import settings
from django.db import models

from apps.businesses.models import Business
from core.models import UUIDTimeStampedModel


class DietaryFlag(models.TextChoices):
    HALAL = "halal", "Halal"
    VEGAN = "vegan", "Vegan"
    VEGETARIAN = "vegetarian", "Vegetarian"
    GLUTEN_FREE = "gluten_free", "Gluten Free"
    SPICY = "spicy", "Spicy"
    NUT_FREE = "nut_free", "Nut Free"


class Menu(UUIDTimeStampedModel):
    """
    A restaurant's menu. One restaurant can have one active menu.
    Menu is tied to a Business with category=restaurant.
    """
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="menu",
    )
    name = models.CharField(
        max_length=255,
        default="Menu",
        help_text="e.g. 'Lunch Menu', 'Full Menu'",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "dining_menu"

    def __str__(self):
        return f"{self.business.name} — {self.name}"


class MenuSection(UUIDTimeStampedModel):
    """
    A section within a menu e.g. Starters, Mains, Drinks, Desserts.
    """
    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    name = models.CharField(max_length=100, help_text="e.g. Starters, Mains, Drinks")
    position = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order — lower number shows first.",
    )

    class Meta:
        db_table = "dining_menu_section"
        ordering = ["position", "name"]

    def __str__(self):
        return f"{self.menu.business.name} — {self.name}"


class MenuItem(UUIDTimeStampedModel):
    """
    A single dish or drink on the menu.
    """
    section = models.ForeignKey(
        MenuSection,
        on_delete=models.CASCADE,
        related_name="items",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    image = models.ImageField(upload_to="dining/menu_items/", blank=True, null=True)
    is_available = models.BooleanField(
        default=True,
        help_text="Uncheck to temporarily hide from customers (e.g. sold out today).",
    )
    dietary_flags = models.JSONField(
        default=list,
        blank=True,
        help_text="List of dietary flags e.g. ['halal', 'spicy']",
    )
    preparation_minutes = models.PositiveSmallIntegerField(
        default=15,
        help_text="Estimated preparation time in minutes.",
    )

    class Meta:
        db_table = "dining_menu_item"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} — ₦{self.price}"


class ReservationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"
    NO_SHOW = "no_show", "No Show"


class Reservation(UUIDTimeStampedModel):
    """
    Table reservation at a restaurant.
    """
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dining_reservations",
    )
    date = models.DateField(help_text="Reservation date.")
    time = models.TimeField(help_text="Reservation time.")
    party_size = models.PositiveSmallIntegerField(help_text="Number of guests.")
    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING,
    )
    special_requests = models.TextField(
        blank=True,
        help_text="e.g. window seat, birthday cake, wheelchair access.",
    )
    rejection_reason = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "dining_reservation"
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.customer} @ {self.business.name} — {self.date} {self.time}"
