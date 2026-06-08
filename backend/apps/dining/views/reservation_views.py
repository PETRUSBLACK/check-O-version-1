from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.businesses.models import Business
from apps.dining.models import Reservation
from apps.dining.serializers import (
    ReservationSerializer,
    ReservationConfirmSerializer,
    ReservationRejectSerializer,
)
from apps.dining.services.reservation import (
    ReservationError,
    cancel_reservation,
    complete_reservation,
    confirm_reservation,
    make_reservation,
    reject_reservation,
)
from core.permissions import IsCustomer, IsVendor


class MakeReservationView(APIView):
    """Customer: make a table reservation at a restaurant."""
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        tags=["dining"],
        summary="Make a table reservation (customer only)",
        request=ReservationSerializer,
        responses={
            201: ReservationSerializer,
            400: None,
            404: None,
        },
    )
    def post(self, request, business_id):
        business = Business.objects.filter(pk=business_id).first()
        if not business:
            return Response({"detail": "Restaurant not found."}, status=404)

        ser = ReservationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        try:
            reservation = make_reservation(
                business=business,
                customer=request.user,
                date=vd["date"],
                time=vd["time"],
                party_size=vd["party_size"],
                special_requests=vd.get("special_requests", ""),
            )
        except ReservationError as e:
            return Response({"detail": str(e)}, status=400)

        return Response(ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)


class CustomerReservationListView(APIView):
    """Customer: list all their reservations."""
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        tags=["dining"],
        summary="List my reservations (customer only)",
        responses={200: ReservationSerializer(many=True)},
    )
    def get(self, request):
        reservations = Reservation.objects.filter(
            customer=request.user
        ).select_related("business")
        return Response(ReservationSerializer(reservations, many=True).data)


class CustomerReservationCancelView(APIView):
    """Customer: cancel their own reservation."""
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        tags=["dining"],
        summary="Cancel my reservation (customer only)",
        responses={200: ReservationSerializer},
    )
    def post(self, request, reservation_id):
        reservation = Reservation.objects.filter(
            pk=reservation_id, customer=request.user
        ).first()
        if not reservation:
            return Response({"detail": "Reservation not found."}, status=404)
        try:
            reservation = cancel_reservation(reservation=reservation, by_customer=True)
        except ReservationError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(ReservationSerializer(reservation).data)


class VendorReservationListView(APIView):
    """Vendor: list all reservations for their restaurant."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=["dining"],
        summary="List restaurant reservations (vendor only)",
        responses={200: ReservationSerializer(many=True)},
    )
    def get(self, request, business_id):
        reservations = Reservation.objects.filter(
            business_id=business_id,
            business__owner=request.user,
        ).select_related("customer")
        return Response(ReservationSerializer(reservations, many=True).data)


class ConfirmReservationView(APIView):
    """Vendor: confirm a pending reservation."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=["dining"],
        summary="Confirm a reservation (vendor only)",
        responses={200: ReservationSerializer},
    )
    def post(self, request, business_id, reservation_id):
        reservation = Reservation.objects.filter(
            pk=reservation_id,
            business_id=business_id,
            business__owner=request.user,
        ).first()
        if not reservation:
            return Response({"detail": "Reservation not found."}, status=404)
        try:
            reservation = confirm_reservation(reservation=reservation)
        except ReservationError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(ReservationSerializer(reservation).data)


class RejectReservationView(APIView):
    """Vendor: reject a pending reservation."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=["dining"],
        summary="Reject a reservation (vendor only)",
        request=ReservationRejectSerializer,
        responses={200: ReservationSerializer},
    )
    def post(self, request, business_id, reservation_id):
        reservation = Reservation.objects.filter(
            pk=reservation_id,
            business_id=business_id,
            business__owner=request.user,
        ).first()
        if not reservation:
            return Response({"detail": "Reservation not found."}, status=404)
        ser = ReservationRejectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            reservation = reject_reservation(
                reservation=reservation,
                reason=ser.validated_data["reason"],
            )
        except ReservationError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(ReservationSerializer(reservation).data)


class CompleteReservationView(APIView):
    """Vendor: mark a confirmed reservation as completed."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=["dining"],
        summary="Complete a reservation (vendor only)",
        responses={200: ReservationSerializer},
    )
    def post(self, request, business_id, reservation_id):
        reservation = Reservation.objects.filter(
            pk=reservation_id,
            business_id=business_id,
            business__owner=request.user,
        ).first()
        if not reservation:
            return Response({"detail": "Reservation not found."}, status=404)
        try:
            reservation = complete_reservation(reservation=reservation)
        except ReservationError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(ReservationSerializer(reservation).data)
