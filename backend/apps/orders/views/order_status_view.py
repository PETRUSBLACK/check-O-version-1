from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order, OrderItem, OrderStatus
from apps.orders.serializers import OrderSerializer
from apps.orders.services.order_service import OrderFlowError, transition_order_status


_VENDOR_TRANSITION_TARGETS = {
    OrderStatus.PROCESSING.value,
    OrderStatus.PACKAGING.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
}


def _vendor_fulfills_order(user, order: Order) -> bool:
    if getattr(user, "role", None) != "vendor":
        return False
    return OrderItem.objects.filter(order=order, product__business__owner=user).exists()


class OrderStatusView(APIView):
    """Workflow: Transition order to a new status."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["orders"], summary="Transition order status", description="POST body must include `status` string.")
    def post(self, request, pk=None):
        to_status = request.data.get("status")
        if not to_status:
            return Response({"detail": "status required"}, status=400)

        order = Order.objects.filter(pk=pk).first()
        if not order:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        role = getattr(request.user, "role", None)
        is_admin = bool(request.user.is_staff or role == "admin")
        is_owner = order.customer_id == request.user.id
        is_fulfillment_vendor = _vendor_fulfills_order(request.user, order)

        if is_admin:
            pass
        elif is_owner:
            if to_status != OrderStatus.CANCELLED.value:
                return Response({"detail": "Customers can only cancel their own orders."}, status=status.HTTP_403_FORBIDDEN)
        elif is_fulfillment_vendor:
            if to_status not in _VENDOR_TRANSITION_TARGETS:
                return Response({"detail": "Vendors may only advance fulfillment (processing, packaging, shipped, delivered)."}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        try:
            transition_order_status(order_id=UUID(str(pk)), to_status=to_status)
        except OrderFlowError as e:
            return Response({"detail": str(e)}, status=400)

        order.refresh_from_db()
        return Response(OrderSerializer(order).data)
