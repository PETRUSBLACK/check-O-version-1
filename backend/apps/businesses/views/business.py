"""
Business API views.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.businesses.choices import BusinessStatus
from apps.businesses.permissions import IsBusinessOwner
from apps.businesses.selectors import get_businesses
from apps.businesses.serializers import (
    BusinessCreateSerializer,
    BusinessDetailSerializer,
    BusinessListSerializer,
    BusinessUpdateSerializer,
)
from apps.businesses.services.registration import (
    BusinessFlowError,
    approve_business,
    reject_business,
    submit_business_for_review,
)
from core.permissions import IsStaffOrPlatformAdmin, IsVendor


class BusinessViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for businesses.
    """

    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """
        Return businesses available to the current request.
        """
        user = self.request.user
        qs = get_businesses()

        if not user or not user.is_authenticated:
            return qs.filter(status=BusinessStatus.APPROVED)

        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs

        if getattr(user, "role", None) == "vendor":
            return qs.filter(owner=user)

        return qs.filter(status=BusinessStatus.APPROVED)

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
        """
        serializer.save()

    def perform_update(self, serializer):
        """
        Update an existing business.
        """
        serializer.save()

    def get_permissions(self):
        """
        Public list/retrieve access for approved businesses.
        Vendor-only create/update/destroy and review actions.
        Admin-only approve/reject actions.
        """
        if self.action in ("list", "retrieve"):
            return [AllowAny()]

        if self.action == "create":
            return [IsAuthenticated(), IsVendor()]

        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsBusinessOwner()]

        if self.action == "submit_for_review":
            return [IsAuthenticated(), IsVendor()]

        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), IsStaffOrPlatformAdmin()]

        return [IsAuthenticated()]

    @action(detail=True, methods=["post"], url_path="submit-for-review")
    def submit_for_review(self, request, *args, **kwargs):
        business = self.get_object()

        if business.owner_id != request.user.id:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        try:
            submit_business_for_review(business_id=business.pk)
        except BusinessFlowError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        business.refresh_from_db()
        return Response(BusinessDetailSerializer(business).data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, *args, **kwargs):
        try:
            business = approve_business(business_id=self.get_object().pk)
        except BusinessFlowError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(BusinessDetailSerializer(business).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, *args, **kwargs):
        reason = request.data.get("reason")
        if not reason or not str(reason).strip():
            return Response({"detail": "rejection_reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            business = reject_business(
                business_id=self.get_object().pk,
                reason=str(reason).strip(),
            )
        except BusinessFlowError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(BusinessDetailSerializer(business).data)