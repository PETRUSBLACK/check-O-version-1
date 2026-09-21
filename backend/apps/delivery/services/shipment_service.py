import logging
from uuid import UUID

from django.db import transaction

from apps.delivery.models import DeliveryMode, Shipment, ShipmentStatus, TrackingEvent
from apps.delivery.providers import LogisticsPartnerProvider, VendorDeliveryProvider
from apps.orders.models import Order, OrderStatus


logger = logging.getLogger(__name__)


class ShipmentError(Exception):
    pass


# Which order status each shipment status corresponds to.
# "pickup" means the rider has collected the parcel from the vendor.
_SHIPMENT_TO_ORDER_STATUS = {
    ShipmentStatus.PROCESSING.value: OrderStatus.PROCESSING.value,
    ShipmentStatus.PACKAGING.value: OrderStatus.PACKAGING.value,
    ShipmentStatus.PICKUP.value: OrderStatus.SHIPPED.value,
    ShipmentStatus.IN_TRANSIT.value: OrderStatus.SHIPPED.value,
    ShipmentStatus.DELIVERED.value: OrderStatus.DELIVERED.value,
}

# The order's delivery path, in sequence.
_ORDER_DELIVERY_PATH = [
    OrderStatus.PAID.value,
    OrderStatus.PROCESSING.value,
    OrderStatus.PACKAGING.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
]


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

    # Keep the order status in step with the shipment
    _sync_order_with_shipment(order_id=shipment.order_id, shipment_status=status)

    return shipment


def _sync_order_with_shipment(*, order_id: UUID, shipment_status: str) -> None:
    """
    Move the order forward along its delivery path until it matches the
    shipment. Each step goes through transition_order_status, so the order
    rules and customer notifications still apply. Never moves an order backwards.
    """
    from apps.orders.services.order_service import OrderFlowError, transition_order_status

    target = _SHIPMENT_TO_ORDER_STATUS.get(shipment_status)
    if not target:
        return

    order = Order.objects.get(pk=order_id)
    if order.status not in _ORDER_DELIVERY_PATH:
        # e.g. cancelled or a pickup order — leave it alone
        logger.warning(
            "shipment_order_sync_skipped order=%s order_status=%s shipment_status=%s",
            order_id, order.status, shipment_status,
        )
        return

    current_index = _ORDER_DELIVERY_PATH.index(order.status)
    target_index = _ORDER_DELIVERY_PATH.index(target)
    for next_status in _ORDER_DELIVERY_PATH[current_index + 1:target_index + 1]:
        try:
            transition_order_status(order_id=order_id, to_status=next_status)
        except OrderFlowError as exc:
            logger.warning(
                "shipment_order_sync_failed order=%s to=%s error=%s",
                order_id, next_status, exc,
            )
            return
