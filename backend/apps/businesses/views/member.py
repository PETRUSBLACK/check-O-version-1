"""
Business member API views.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.businesses.selectors import (
    get_members,
)

from apps.businesses.serializers import (
    BusinessMemberListSerializer,
    BusinessMemberDetailSerializer,
    BusinessMemberCreateSerializer,
    BusinessMemberUpdateSerializer,
)


class BusinessMemberViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for business members.
    """

    permission_classes = (
        IsAuthenticated,
    )

    def get_queryset(self):
        return get_members()

    def get_serializer_class(self):

        if self.action == "list":
            return BusinessMemberListSerializer

        if self.action == "retrieve":
            return BusinessMemberDetailSerializer

        if self.action == "create":
            return BusinessMemberCreateSerializer

        if self.action in (
            "update",
            "partial_update",
        ):
            return BusinessMemberUpdateSerializer

        return BusinessMemberDetailSerializer