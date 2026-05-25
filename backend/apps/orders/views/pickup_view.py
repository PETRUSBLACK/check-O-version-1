from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order, OrderStatus
from apps.orders.serializers import OrderSerializer
from apps.orders.services.order_service import OrderFlowError, transition_order_status
from core.permissions import IsVendorOrAdmin


class MarkReadyForPickupView(APIView):
    """Workflow: Vendor marks order as ready for customer pickup."""
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    @extend_schema(tags=["orders"], summary="Mark order ready for pickup")
    def post(self, request, pk=None):
        order = Order.objects.filter(pk=pk).first()
        if not order:
            return Response({"detail": "Order not found."}, status=404)
        if order.fulfilment_type != "pickup":
            return Response({"detail": "This order is not a pickup order."}, status=400)
        try:
            transition_order_status(order_id=order.pk, to_status=OrderStatus.READY_FOR_PICKUP.value)
        except OrderFlowError as e:
            return Response({"detail": str(e)}, status=400)
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)


class ConfirmPickupView(APIView):
    """Workflow: Vendor confirms customer collected order using pickup code."""
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    @extend_schema(tags=["orders"], summary="Confirm customer collected order (vendor scans pickup code)")
    def post(self, request, pk=None):
        pickup_code = request.data.get("pickup_code", "").strip()
        if not pickup_code:
            return Response({"detail": "pickup_code required."}, status=400)

        order = Order.objects.filter(pk=pk).first()
        if not order:
            return Response({"detail": "Order not found."}, status=404)

        if order.pickup_code != pickup_code:
            return Response({"detail": "Invalid pickup code."}, status=400)

        if order.status != OrderStatus.READY_FOR_PICKUP.value:
            return Response({"detail": "Order is not in ready-for-pickup status."}, status=400)

        try:
            transition_order_status(order_id=order.pk, to_status=OrderStatus.COLLECTED.value)
        except OrderFlowError as e:
            return Response({"detail": str(e)}, status=400)

        order.refresh_from_db()
        return Response(OrderSerializer(order).data)
