from uuid import UUID

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order

from .models import Payment
from .serializers import PaymentSerializer
from .services.gateway import confirm_payment_success, initiate_payment


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        qs = self.queryset.select_related("order")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs.order_by("-created_at")
        return qs.filter(order__customer=user).order_by("-created_at")

    @action(detail=False, methods=["post"])
    @extend_schema(
        tags=["payments"],
        summary="Initiate a payment for current user's order",
    )
    def initiate(self, request):
        role = getattr(request.user, "role", None)
        if role != "customer":
            return Response(
                {"detail": "Only customers can initiate payment."},
                status=status.HTTP_403_FORBIDDEN,
            )
        order_id = request.data.get("order_id")
        provider = request.data.get("provider")
        if not order_id or not provider:
            return Response({"detail": "order_id and provider required"}, status=400)
        order = Order.objects.filter(pk=order_id, customer=request.user).first()
        if not order:
            return Response({"detail": "Order not found"}, status=404)
        try:
            payment = initiate_payment(
                order_id=UUID(str(order_id)),
                provider=str(provider),
                amount=order.total,
            )
        except ValueError:
            return Response(
                {"detail": "Invalid provider or order already paid"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    @extend_schema(
        tags=["payments"],
        summary="Mock-confirm payment success (admin only)",
    )
    def mock_confirm(self, request, pk=None):
        try:
            payment = confirm_payment_success(payment_id=UUID(str(pk)))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data)
