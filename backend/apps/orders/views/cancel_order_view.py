from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import CancellationReason, Order
from apps.orders.serializers import OrderSerializer
from apps.orders.services.order_service import (
    OrderFlowError,
    OrderPermissionError,
    cancel_order,
)


class CancelOrderSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(
        choices=[
            CancellationReason.OUT_OF_STOCK,
            CancellationReason.ITEM_DAMAGED,
            CancellationReason.OTHER,
        ],
        required=False,
        help_text="Required for vendors. Ignored for customers.",
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required for vendors when reason is 'other'.",
    )


class CancelOrderView(APIView):
    """
    Workflow: Cancel an order.

    - Customer: while unpaid, or paid but the shop has not started on it.
    - Vendor: any time before the goods leave the shop, with a reason.
    - Admin: same window as vendor.
    Stock is returned automatically. Paid orders are flagged for refund.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CancelOrderSerializer,
        responses={200: OrderSerializer},
        tags=["orders"],
        summary="Cancel an order",
        description=(
            "Customers can cancel until the shop starts processing the order. "
            "Vendors can cancel until the order ships and must give a `reason` "
            "(`out_of_stock`, `item_damaged`, or `other` with a `note`). "
            "Held stock is returned; paid orders are marked `refund_status=due`."
        ),
    )
    def post(self, request, pk=None):
        ser = CancelOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        if not Order.objects.filter(pk=pk).exists():
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            order = cancel_order(
                order_id=UUID(str(pk)),
                user=request.user,
                reason=ser.validated_data.get("reason", ""),
                note=ser.validated_data.get("note", ""),
            )
        except OrderPermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except OrderFlowError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data)
