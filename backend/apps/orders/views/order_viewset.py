from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.orders.models import Order
from apps.orders.serializers import OrderCreateSerializer, OrderSerializer
from apps.orders.services.order_service import OrderFlowError, create_order_with_lines
from core.permissions import IsCustomer


@extend_schema_view(
    list=extend_schema(
        tags=["orders"],
        summary="List orders",
        description="Customers see their own orders. Vendors see orders containing their products. Admins see all.",
    ),
    retrieve=extend_schema(
        tags=["orders"],
        summary="Get order detail",
    ),
)
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD: Order read and creation."""
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
            return qs.filter(items__product__business__owner=user).distinct().order_by("-created_at")
        return qs.filter(customer=user).order_by("-created_at")

    @extend_schema(
        request=OrderCreateSerializer,
        responses={201: OrderSerializer},
        tags=["orders"],
        summary="Create order with line items",
        description="Directly create an order with line items. Prefer using cart checkout instead.",
    )
    def create(self, request, *args, **kwargs):
        if not IsCustomer().has_permission(request, self):
            return Response({"detail": "Only customers can create orders."}, status=status.HTTP_403_FORBIDDEN)
        ser = OrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            order = create_order_with_lines(customer=request.user, lines=ser.validated_data["items"])
        except OrderFlowError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
