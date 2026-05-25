from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.users.models import User
from apps.users.serializers import UserSerializer


@extend_schema_view(
    list=extend_schema(tags=["users"], summary="List users (admin sees all, others see self only)"),
    retrieve=extend_schema(tags=["users"], summary="Get a user by ID"),
)
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """CRUD: Read-only access to user records."""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        base = User.objects.all().order_by("-date_joined")
        if user.is_staff:
            return base
        return base.filter(pk=user.pk)
