"""
Business API views.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.businesses.permissions import IsBusinessOwner

from apps.businesses.selectors import get_businesses

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

    def get_queryset(self):
        """
        Return businesses available to the current request.

        Using a method instead of a class-level queryset makes it
        easy to add filtering based on the authenticated user,
        permissions, or query parameters in the future.
        """
        return get_businesses()

    def get_serializer_class(self):
        """
        Return the appropriate serializer for each action.
        """

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
        """
        Create a new business.

        The serializer delegates the creation to the
        create_business() service.
        """
        serializer.save()


    def perform_update(self, serializer):
        """
        Update an existing business.

        The serializer delegates the update to the
        update_business() service.
        """
        serializer.save()

    def get_permissions(self):
        """
        Owners can modify their businesses.
        Everyone authenticated can list/retrieve.
        """

        if self.action in (
            "update",
            "partial_update",
            "destroy",
        ):
            return [
                IsAuthenticated(),
                IsBusinessOwner(),
            ]

        return [
            IsAuthenticated(),
        ]