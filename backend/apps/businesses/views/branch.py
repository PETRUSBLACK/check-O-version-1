"""
Branch API views.
"""

from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.businesses.models import Business

from apps.businesses.selectors import (
    get_branches,
    get_business_branches,
)

from apps.businesses.serializers import (
    BranchListSerializer,
    BranchDetailSerializer,
    BranchCreateSerializer,
    BranchUpdateSerializer,
)


class BranchViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for business branches.
    """

    permission_classes = (
        IsAuthenticated,
    )

    def get_queryset(self):
        """
        Return branches.

        If a business_id is supplied in the URL,
        only return branches for that business.
        """

        business_id = self.kwargs.get("business_id")

        if business_id:
            business = get_object_or_404(
                Business,
                pk=business_id,
            )

            return get_business_branches(
                business=business,
            )

        return get_branches()

    def get_serializer_class(self):

        if self.action == "list":
            return BranchListSerializer

        if self.action == "retrieve":
            return BranchDetailSerializer

        if self.action == "create":
            return BranchCreateSerializer

        if self.action in (
            "update",
            "partial_update",
        ):
            return BranchUpdateSerializer

        return BranchDetailSerializer

    def get_serializer_context(self):
        """
        Add the business instance to serializer context
        during branch creation.
        """

        context = super().get_serializer_context()

        business_id = self.kwargs.get("business_id")

        if business_id:

            context["business"] = get_object_or_404(
                Business,
                pk=business_id,
            )

        return context