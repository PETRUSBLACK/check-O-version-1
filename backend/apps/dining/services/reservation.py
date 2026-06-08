import datetime

from django.db import transaction
from django.utils import timezone

from apps.businesses.models import Business, BusinessCategory
from apps.dining.models import Reservation, ReservationStatus


class ReservationError(Exception):
    pass


def _assert_restaurant(business: Business):
    if business.category != BusinessCategory.RESTAURANT:
        raise ReservationError("This business is not registered as a restaurant.")


@transaction.atomic
def make_reservation(
    *,
    business: Business,
    customer,
    date: datetime.date,
    time: datetime.time,
    party_size: int,
    special_requests: str = "",
) -> Reservation:
    _assert_restaurant(business)

    # Cannot book in the past
    reservation_dt = datetime.datetime.combine(date, time)
    if reservation_dt < datetime.datetime.now():
        raise ReservationError("Cannot make a reservation in the past.")

    # One active reservation per customer per restaurant per day
    existing = Reservation.objects.filter(
        business=business,
        customer=customer,
        date=date,
        status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED],
    ).exists()
    if existing:
        raise ReservationError(
            "You already have an active reservation at this restaurant on this date."
        )

    return Reservation.objects.create(
        business=business,
        customer=customer,
        date=date,
        time=time,
        party_size=party_size,
        special_requests=special_requests,
        status=ReservationStatus.PENDING,
    )


@transaction.atomic
def confirm_reservation(*, reservation: Reservation) -> Reservation:
    if reservation.status != ReservationStatus.PENDING:
        raise ReservationError("Only pending reservations can be confirmed.")
    reservation.status = ReservationStatus.CONFIRMED
    reservation.confirmed_at = timezone.now()
    reservation.save(update_fields=["status", "confirmed_at", "updated_at"])
    return reservation


@transaction.atomic
def reject_reservation(*, reservation: Reservation, reason: str) -> Reservation:
    if reservation.status != ReservationStatus.PENDING:
        raise ReservationError("Only pending reservations can be rejected.")
    if not reason or not reason.strip():
        raise ReservationError("Rejection reason is required.")
    reservation.status = ReservationStatus.CANCELLED
    reservation.rejection_reason = reason.strip()
    reservation.cancelled_at = timezone.now()
    reservation.save(update_fields=["status", "rejection_reason", "cancelled_at", "updated_at"])
    return reservation


@transaction.atomic
def cancel_reservation(*, reservation: Reservation, by_customer: bool = True) -> Reservation:
    if reservation.status not in (ReservationStatus.PENDING, ReservationStatus.CONFIRMED):
        raise ReservationError("This reservation cannot be cancelled.")
    reservation.status = ReservationStatus.CANCELLED
    reservation.cancelled_at = timezone.now()
    reservation.save(update_fields=["status", "cancelled_at", "updated_at"])
    return reservation


@transaction.atomic
def complete_reservation(*, reservation: Reservation) -> Reservation:
    if reservation.status != ReservationStatus.CONFIRMED:
        raise ReservationError("Only confirmed reservations can be marked as completed.")
    reservation.status = ReservationStatus.COMPLETED
    reservation.save(update_fields=["status", "updated_at"])
    return reservation
