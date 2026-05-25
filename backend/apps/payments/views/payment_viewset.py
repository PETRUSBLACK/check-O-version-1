from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer
from drf_spectacular.utils import extend_schema


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """CRUD: Payment read-only access."""
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
