from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer, UnreadCountSerializer


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
    """
    A person's own inbox.

    Read-only apart from marking things read — a notification is a record of
    something that happened, so there is no sense in editing the words or
    creating one from a phone.
    """

    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        # Scoped to the owner, not filtered by a query parameter — so there is
        # no id anyone can guess that reaches someone else's messages.
        return self.queryset.filter(user=user).order_by("-created_at")

    @extend_schema(
        tags=["notifications"],
        summary="How many unread notifications you have",
        responses={200: UnreadCountSerializer},
    )
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        """
        The number on the bell. Its own endpoint because every screen in the app
        wants it, and paging the whole inbox to count unread rows would be a
        silly thing to do on a phone on Nigerian mobile data.
        """
        count = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({"unread": count})

    @extend_schema(
        tags=["notifications"],
        summary="Mark one notification as read",
        request=None,
        responses={200: NotificationSerializer},
    )
    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        """Idempotent: reading something twice does not move the timestamp."""
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @extend_schema(
        tags=["notifications"],
        summary="Mark every notification as read",
        request=None,
        responses={200: OpenApiResponse(description='{"marked": <number>}')},
    )
    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        """
        One tap to clear the badge. Anyone arriving at an inbox with months of
        unread messages in it needs this, and Check-O has been storing them
        since September with nothing able to read them.
        """
        marked = self.get_queryset().filter(read_at__isnull=True).update(
            read_at=timezone.now()
        )
        return Response({"marked": marked}, status=status.HTTP_200_OK)
