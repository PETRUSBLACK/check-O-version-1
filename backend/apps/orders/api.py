from uuid import UUID

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order, OrderItem, OrderStatus
from apps.orders.serializers import OrderCreateSerializer, OrderSerializer
from apps.orders.services.order_service import (
    OrderFlowError,
    create_order_with_lines,
    transition_order_status,
)
from core.permissions import IsCustomer

# Vendor may advance fulfillment after payment (same as order state machine forward steps).
_VENDOR_TRANSITION_TARGETS = {
    OrderStatus.PROCESSING.value,
    OrderStatus.PACKAGING.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
}


def _vendor_fulfills_order(user, order: Order) -> bool:
    if getattr(user, "role", None) != "vendor":
        return False
    return OrderItem.objects.filter(
        order=order,
        product__business__owner=user,
    ).exists()


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        qs = self.queryset.prefetch_related("items__product")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs.order_by("-created_at")
        if getattr(user, "role", None) == "vendor":
            return (
                qs.filter(items__product__business__owner=user)
                .distinct()
                .order_by("-created_at")
            )
        return qs.filter(customer=user).order_by("-created_at")

    @extend_schema(
        request=OrderCreateSerializer,
        responses={201: OrderSerializer},
        tags=["orders"],
        summary="Create order with line items",
    )
    def create(self, request, *args, **kwargs):
        if not IsCustomer().has_permission(request, self):
            return Response(
                {"detail": "Only customers can create orders."},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = OrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            order = create_order_with_lines(
                customer=request.user,
                lines=ser.validated_data["items"],
            )
        except OrderFlowError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        headers = self.get_success_headers(OrderSerializer(order).data)
        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @action(detail=True, methods=["post"], url_path="transition")
    @extend_schema(
        request=None,
        responses={200: OrderSerializer},
        tags=["orders"],
        summary="Transition order status",
        description="POST body must include `status` string.",
    )
    def transition(self, request, pk=None):
        to_status = request.data.get("status")
        if not to_status:
            return Response({"detail": "status required"}, status=400)
        order = self.get_object()
        role = getattr(request.user, "role", None)
        is_admin = bool(request.user.is_staff or role == "admin")
        is_owner = order.customer_id == request.user.id
        is_fulfillment_vendor = _vendor_fulfills_order(request.user, order)

        if is_admin:
            pass
        elif is_owner:
            if to_status != OrderStatus.CANCELLED.value:
                return Response(
                    {"detail": "Customers can only cancel their own orders."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif is_fulfillment_vendor:
            if to_status not in _VENDOR_TRANSITION_TARGETS:
                return Response(
                    {
                        "detail": "Vendors may only advance fulfillment "
                        "(processing, packaging, shipped, delivered).",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        try:
            transition_order_status(order_id=UUID(str(pk)), to_status=to_status)
        except OrderFlowError as e:
            return Response({"detail": str(e)}, status=400)
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)
