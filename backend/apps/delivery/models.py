from django.db import models

from apps.orders.models import Order
from core.models import UUIDTimeStampedModel


class DeliveryMode(models.TextChoices):
    VENDOR_MANAGED = "vendor_managed", "Vendor managed"
    PARTNER = "partner", "Logistics partner"


class LogisticsProvider(models.TextChoices):
    GIG = "gig", "GIG Logistics"
    KWIK = "kwik", "Kwik Delivery"
    DHL = "dhl", "DHL"


class ShipmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    PACKAGING = "packaging", "Packaging"
    PICKUP = "pickup", "Pickup"
    IN_TRANSIT = "in_transit", "In transit"
    DELIVERED = "delivered", "Delivered"


class Shipment(UUIDTimeStampedModel):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="shipment",
    )
    mode = models.CharField(max_length=32, choices=DeliveryMode.choices)
    partner = models.CharField(
        max_length=32,
        choices=LogisticsProvider.choices,
        blank=True,
    )
    tracking_number = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=32,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.PENDING,
    )

    class Meta:
        db_table = "delivery_shipment"


class TrackingEvent(UUIDTimeStampedModel):
    """
    Immutable log of every shipment status change.
    Gives customers full visibility of their delivery journey.
    """
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="tracking_events",
    )
    status = models.CharField(max_length=32, choices=ShipmentStatus.choices)
    note = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tracking_events",
    )

    class Meta:
        db_table = "delivery_trackingevent"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.shipment_id} → {self.status}"
