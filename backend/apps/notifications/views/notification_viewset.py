from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


@extend_schema_view(
    list=extend_schema(tags=["notifications"], summary="List your notifications (newest first)"),
    retrieve=extend_schema(tags=["notifications"], summary="Get a notification"),
    update=extend_schema(tags=["notifications"], summary="Update notification (e.g. mark as read)"),
    partial_update=extend_schema(tags=["notifications"], summary="Partially update notification"),
)
class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD: Notification read and mark-as-read."""
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(user=user).order_by("-created_at")
