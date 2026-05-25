from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.businesses.models import Business
from apps.subscriptions.models import VendorSubscription
from apps.subscriptions.serializers import VendorSubscriptionSerializer
from core.permissions import IsVendorOrAdmin


@extend_schema_view(
    list=extend_schema(tags=["subscriptions"], summary="List vendor's subscriptions"),
    retrieve=extend_schema(tags=["subscriptions"], summary="Get subscription detail"),
)
class VendorSubscriptionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD: Vendor subscription read access."""
    queryset = VendorSubscription.objects.all()
    serializer_class = VendorSubscriptionSerializer
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return self.queryset.select_related("plan", "business").order_by("-created_at")
        ids = Business.objects.filter(owner=user).values_list("id", flat=True)
        return self.queryset.filter(business_id__in=ids).select_related("plan").order_by("-created_at")
