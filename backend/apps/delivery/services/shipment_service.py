from uuid import UUID

from django.db import transaction

from apps.delivery.models import DeliveryMode, Shipment, ShipmentStatus, TrackingEvent
from apps.delivery.providers import LogisticsPartnerProvider, VendorDeliveryProvider
from apps.orders.models import Order, OrderStatus


class ShipmentError(Exception):
    pass


_ALLOWED_TRANSITIONS = {
    ShipmentStatus.PENDING.value: {ShipmentStatus.PROCESSING.value},
    ShipmentStatus.PROCESSING.value: {ShipmentStatus.PACKAGING.value},
    ShipmentStatus.PACKAGING.value: {ShipmentStatus.PICKUP.value},
    ShipmentStatus.PICKUP.value: {ShipmentStatus.IN_TRANSIT.value},
    ShipmentStatus.IN_TRANSIT.value: {ShipmentStatus.DELIVERED.value},
    ShipmentStatus.DELIVERED.value: set(),
}


@transaction.atomic
def create_shipment(*, order_id: UUID, mode: str, partner: str = "", tracking_number: str = "") -> Shipment:
    order = Order.objects.select_for_update().get(pk=order_id)

    if order.status not in (OrderStatus.PAID.value, OrderStatus.PROCESSING.value):
        raise ShipmentError("A shipment can only be created for a paid or processing order.")

    if Shipment.objects.filter(order=order).exists():
        raise ShipmentError("A shipment already exists for this order.")

    if mode == DeliveryMode.PARTNER and not partner:
        raise ShipmentError("A logistics partner must be specified for partner delivery.")

    shipment = Shipment.objects.create(
        order=order,
        mode=mode,
        partner=partner,
        tracking_number=tracking_number,
        status=ShipmentStatus.PENDING,
    )

    # Assign via provider
    if mode == DeliveryMode.VENDOR_MANAGED:
        provider = VendorDeliveryProvider()
        result = provider.assign(shipment=shipment)
    else:
        provider = LogisticsPartnerProvider(partner=partner)
        result = provider.book(shipment=shipment)

    if not tracking_number:
        shipment.tracking_number = result.get("booking_ref") or result.get("tracking_number", "")
        shipment.save(update_fields=["tracking_number", "updated_at"])

    # Log initial tracking event
    TrackingEvent.objects.create(
        shipment=shipment,
        status=ShipmentStatus.PENDING,
        note="Shipment created.",
    )

    return shipment


@transaction.atomic
def update_shipment_status(*, shipment_id: UUID, status: str, note: str = "", location: str = "", recorded_by=None) -> Shipment:
    valid = {s.value for s in ShipmentStatus}
    if status not in valid:
        raise ShipmentError(f"Invalid shipment status: {status}")

    shipment = Shipment.objects.select_for_update().select_related("order__customer").get(pk=shipment_id)

    if shipment.status == status:
        return shipment

    allowed = _ALLOWED_TRANSITIONS.get(shipment.status, set())
    if status not in allowed:
        raise ShipmentError(f"Cannot transition shipment from '{shipment.status}' to '{status}'.")

    shipment.status = status
    shipment.save(update_fields=["status", "updated_at"])

    # Log tracking event
    TrackingEvent.objects.create(
        shipment=shipment,
        status=status,
        note=note,
        location=location,
        recorded_by=recorded_by,
    )

    # Fire notification
    from apps.notifications.services.notification_service import notify_shipment_updated
    notify_shipment_updated(shipment=shipment)

    # Auto-mark order delivered when shipment delivered
    if status == ShipmentStatus.DELIVERED.value:
        from apps.orders.services.order_service import OrderFlowError, transition_order_status
        try:
            transition_order_status(order_id=shipment.order_id, to_status=OrderStatus.DELIVERED.value)
        except OrderFlowError:
            pass

    return shipment
