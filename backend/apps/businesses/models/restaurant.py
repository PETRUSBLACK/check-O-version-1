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
    """

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="restaurant_profile",
    )

    cuisine = models.CharField(
        max_length=120,
        help_text="Example: Nigerian, Chinese, Italian.",
    )

    average_preparation_time = models.PositiveIntegerField(
        default=30,
        help_text="Preparation time in minutes.",
    )

    accepts_reservations = models.BooleanField(default=True)

    accepts_takeaway = models.BooleanField(default=True)

    accepts_delivery = models.BooleanField(default=True)

    serves_breakfast = models.BooleanField(default=False)

    serves_lunch = models.BooleanField(default=True)

    serves_dinner = models.BooleanField(default=True)

    has_wifi = models.BooleanField(default=False)

    has_parking = models.BooleanField(default=False)

    has_outdoor_seating = models.BooleanField(default=False)

    class Meta:
        db_table = "businesses_restaurant_profile"

    def __str__(self):
        return self.business.name