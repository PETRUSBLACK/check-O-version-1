from uuid import UUID

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.orders.models import OrderItem
from core.permissions import IsVendorOrAdmin

from .models import Shipment
from .serializers import ShipmentSerializer
from .services.shipment_service import create_shipment, update_shipment_status


class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        qs = self.queryset.select_related("order__customer")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs.order_by("-created_at")
        if getattr(user, "role", None) == "vendor":
            return qs.filter(order__items__product__business__owner=user).distinct()
        return qs.filter(order__customer=user).order_by("-created_at")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsVendorOrAdmin()]
        return [IsAuthenticated()]

    @extend_schema(
        request=ShipmentSerializer,
        responses={201: ShipmentSerializer},
        tags=["delivery"],
        summary="Create shipment for order",
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.validated_data["order"]
        user = request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if getattr(user, "role", None) == "vendor":
                has_line = OrderItem.objects.filter(
                    order=order,
                    product__business__owner=user,
                ).exists()
                if not has_line:
                    return Response(
                        {
                            "detail": "You can only create shipments for orders that "
                            "include products from your business."
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
        try:
            shipment = create_shipment(
                order_id=order.pk,
                mode=serializer.validated_data["mode"],
                partner=serializer.validated_data.get("partner", ""),
                tracking_number=serializer.validated_data.get("tracking_number", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ShipmentSerializer(shipment).data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(ShipmentSerializer(shipment).data),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="status",
        permission_classes=[IsAuthenticated, IsVendorOrAdmin],
    )
    @extend_schema(
        tags=["delivery"],
        summary="Update shipment status",
        description="POST body must include `status` string.",
    )
    def set_status(self, request, pk=None):
        shipment = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "status required"}, status=400)
        try:
            shipment = update_shipment_status(
                shipment_id=shipment.pk,
                status=new_status,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ShipmentSerializer(shipment).data)
