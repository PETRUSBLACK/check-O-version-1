"""
Business API views.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.businesses.selectors import (
    get_businesses,
)

from apps.businesses.services import (
    create_business,
    update_business,
)

from apps.businesses.serializers import (
    BusinessListSerializer,
    BusinessDetailSerializer,
    BusinessCreateSerializer,
    BusinessUpdateSerializer,
)


class BusinessViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for businesses.
    """

    permission_classes = (
        IsAuthenticated,
    )

    queryset = get_businesses()

    def get_serializer_class(self):

        if self.action == "list":
            return BusinessListSerializer

        if self.action == "retrieve":
            return BusinessDetailSerializer

        if self.action == "create":
            return BusinessCreateSerializer

        if self.action in ("update", "partial_update"):
            return BusinessUpdateSerializer

        return BusinessDetailSerializer

    def perform_create(self, serializer):
        create_business(
            owner=self.request.user,
            **serializer.validated_data,
        )

    def perform_update(self, serializer):
        update_business(
            serializer.instance,
            **serializer.validated_data,
        )