"""
Branch API views.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.businesses.selectors import get_branches

from apps.businesses.services import (
    create_branch,
    update_branch,
)

from apps.businesses.serializers import (
    BranchListSerializer,
    BranchDetailSerializer,
    BranchCreateSerializer,
    BranchUpdateSerializer,
)


class BranchViewSet(viewsets.ModelViewSet):

    permission_classes = (
        IsAuthenticated,
    )

    queryset = get_branches()

    def get_serializer_class(self):

        if self.action == "list":
            return BranchListSerializer

        if self.action == "retrieve":
            return BranchDetailSerializer

        if self.action == "create":
            return BranchCreateSerializer

        if self.action in ("update", "partial_update"):
            return BranchUpdateSerializer

        return BranchDetailSerializer

    def perform_create(self, serializer):
        create_branch(
            **serializer.validated_data,
        )

    def perform_update(self, serializer):
        update_branch(
            serializer.instance,
            **serializer.validated_data,
        )