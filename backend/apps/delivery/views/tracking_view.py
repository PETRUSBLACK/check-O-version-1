from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.delivery.models import Shipment, TrackingEvent
from apps.delivery.serializers import ShipmentSerializer


class TrackingEventSerializer:
    pass


from rest_framework import serializers

class TrackingEventOutputSerializer(serializers.ModelSerializer):
    recorded_by_email = serializers.EmailField(source="recorded_by.email", read_only=True, default=None)

    class Meta:
        model = TrackingEvent
        fields = ("id", "status", "note", "location", "recorded_by_email", "created_at")


class TrackingHistoryView(APIView):
    """
    Public: Get full tracking history for a shipment by tracking number.
    Customers use this to track their delivery journey.
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=["delivery"], summary="Get shipment tracking history by tracking number")
    def get(self, request, tracking_number=None):
        shipment = Shipment.objects.filter(tracking_number=tracking_number).select_related("order__customer").first()
        if not shipment:
            return Response({"detail": "Shipment not found."}, status=404)

        events = shipment.tracking_events.select_related("recorded_by").all()
        return Response({
            "shipment": ShipmentSerializer(shipment).data,
            "tracking_events": TrackingEventOutputSerializer(events, many=True).data,
        })


class ShipmentTrackingView(APIView):
    """
    Authenticated: Get tracking history for a shipment by shipment ID.
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=["delivery"], summary="Get tracking events for a shipment")
    def get(self, request, pk=None):
        shipment = Shipment.objects.filter(pk=pk).first()
        if not shipment:
            return Response({"detail": "Shipment not found."}, status=404)
        events = shipment.tracking_events.select_related("recorded_by").all()
        return Response({
            "shipment": ShipmentSerializer(shipment).data,
            "tracking_events": TrackingEventOutputSerializer(events, many=True).data,
        })
