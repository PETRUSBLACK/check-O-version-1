from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer
from apps.payments.services.gateway import confirm_payment_success, initiate_payment


class InitiatePaymentView(APIView):
    """Workflow: Initiate payment for an order."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["payments"], summary="Initiate a payment for current user's order")
    def post(self, request):
        if getattr(request.user, "role", None) != "customer":
            return Response({"detail": "Only customers can initiate payment."}, status=status.HTTP_403_FORBIDDEN)
        order_id = request.data.get("order_id")
        provider = request.data.get("provider")
        if not order_id or not provider:
            return Response({"detail": "order_id and provider required"}, status=400)
        order = Order.objects.filter(pk=order_id, customer=request.user).first()
        if not order:
            return Response({"detail": "Order not found"}, status=404)
        try:
            payment, payment_url = initiate_payment(order_id=UUID(str(order_id)), provider=str(provider), amount=order.total)
        except ValueError:
            return Response({"detail": "Invalid provider or order already paid"}, status=status.HTTP_400_BAD_REQUEST)
        data = PaymentSerializer(payment).data
        data["payment_url"] = payment_url
        return Response(data, status=status.HTTP_201_CREATED)


class MockConfirmPaymentView(APIView):
    """Workflow: Mock-confirm payment success (admin only)."""
    permission_classes = [IsAdminUser]

    @extend_schema(tags=["payments"], summary="Mock-confirm payment success (admin only)")
    def post(self, request, pk=None):
        try:
            payment = confirm_payment_success(payment_id=UUID(str(pk)))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data)
