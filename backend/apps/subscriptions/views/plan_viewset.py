from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.subscriptions.models import SubscriptionPlan
from apps.subscriptions.serializers import SubscriptionPlanSerializer


@extend_schema_view(
    list=extend_schema(tags=["subscriptions"], summary="List all available subscription plans"),
    retrieve=extend_schema(tags=["subscriptions"], summary="Get subscription plan detail"),
)
class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """CRUD: Public read-only access to subscription plans."""
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by("price_monthly")
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]
