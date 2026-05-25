from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, viewsets

from apps.analytics.models import AnalyticsEvent
from apps.analytics.serializers import AnalyticsEventSerializer


@extend_schema_view(
    create=extend_schema(
        tags=["analytics"],
        summary="Track a platform event (public — no auth required)",
        description="Use this to track events like product_view, search, page_view from the frontend.",
    ),
)
class AnalyticsEventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """CRUD: Analytics event tracking."""
    serializer_class = AnalyticsEventSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)
