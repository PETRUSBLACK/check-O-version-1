from rest_framework import mixins, permissions, viewsets

from .models import AnalyticsEvent
from .serializers import AnalyticsEventSerializer


class AnalyticsEventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = AnalyticsEventSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)
