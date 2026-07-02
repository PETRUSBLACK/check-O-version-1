"""
Restaurant-specific profile.

Only businesses with category=RESTAURANT should
have a RestaurantProfile.
"""

from django.db import models

from core.models import UUIDTimeStampedModel

from .business import Business


class RestaurantProfile(UUIDTimeStampedModel):
    """
    Additional information for restaurant businesses.

    This model stores restaurant-specific settings that do not
    apply to other business categories such as supermarkets,
    pharmacies, or retail stores.
    """

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="restaurant_profile",
        help_text="Restaurant business.",
    )

    cuisine = models.CharField(
        max_length=120,
        help_text="Example: Nigerian, Chinese, Italian, Continental.",
    )

    average_preparation_time = models.PositiveIntegerField(
        default=30,
        help_text="Average food preparation time in minutes.",
    )

    average_cost_for_two = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated average cost for two people.",
    )

    maximum_table_capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of diners the restaurant can accommodate.",
    )

    accepts_reservations = models.BooleanField(
        default=True,
        help_text="Customers can reserve tables.",
    )

    accepts_takeaway = models.BooleanField(
        default=True,
        help_text="Customers can place takeaway orders.",
    )

    accepts_delivery = models.BooleanField(
        default=True,
        help_text="Restaurant offers delivery services.",
    )

    accepts_online_payment = models.BooleanField(
        default=True,
        help_text="Restaurant accepts online payments.",
    )

    serves_breakfast = models.BooleanField(
        default=False,
    )

    serves_lunch = models.BooleanField(
        default=True,
    )

    serves_dinner = models.BooleanField(
        default=True,
    )

    has_wifi = models.BooleanField(
        default=False,
    )

    has_parking = models.BooleanField(
        default=False,
    )

    has_outdoor_seating = models.BooleanField(
        default=False,
    )

    class Meta:
        db_table = "businesses_restaurant_profile"
        verbose_name = "Restaurant Profile"
        verbose_name_plural = "Restaurant Profiles"

        indexes = [
            models.Index(fields=["business"]),
        ]

    def __str__(self):
        return f"{self.business.name} Restaurant"

    @property
    def supports_online_ordering(self):
        """
        Returns True if customers can place online orders.
        """
        return (
            self.accepts_delivery
            or self.accepts_takeaway
        )