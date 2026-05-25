from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.permissions import IsVendorOrAdmin
from apps.delivery.models import Shipment
from apps.delivery.serializers import ShipmentSerializer
from apps.delivery.services.shipment_service import ShipmentError, update_shipment_status


class ShipmentStatusView(APIView):
    """Workflow: Update shipment tracking status."""
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    @extend_schema(tags=["delivery"], summary="Update shipment status")
    def post(self, request, pk=None):
        shipment = Shipment.objects.filter(pk=pk).first()
        if not shipment:
            return Response({"detail": "Shipment not found."}, status=404)
        new_status = request.data.get("status")
        note = request.data.get("note", "")
        location = request.data.get("location", "")
        if not new_status:
            return Response({"detail": "status required"}, status=400)
        try:
            shipment = update_shipment_status(
                shipment_id=shipment.pk,
                status=new_status,
                note=note,
                location=location,
                recorded_by=request.user,
            )
        except ShipmentError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ShipmentSerializer(shipment).data)
