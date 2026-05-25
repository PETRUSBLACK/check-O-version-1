from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from core.permissions import IsStaffOrPlatformAdmin, IsVendor

from .models import Business, BusinessStatus
from .serializers import BusinessRejectSerializer, BusinessSerializer
from .services.registration import (
    BusinessFlowError,
    approve_business,
    reject_business,
    register_business,
    submit_business_for_review,
)


class BusinessViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsVendor()]
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsVendor()]
        if self.action in ("approve", "reject"):
            return [permissions.IsAuthenticated(), IsStaffOrPlatformAdmin()]
        if self.action == "submit_for_review":
            return [permissions.IsAuthenticated(), IsVendor()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Business.objects.select_related("owner").all()
        user = self.request.user
        if not user.is_authenticated:
            return qs.filter(status=BusinessStatus.APPROVED)
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        if getattr(user, "role", None) == "vendor":
            return qs.filter(owner=user)
        return qs.filter(status=BusinessStatus.APPROVED)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        business = register_business(
            owner=request.user,
            name=vd["name"],
            slug=vd["slug"],
            legal_name=vd.get("legal_name") or "",
            registration_number=vd.get("registration_number") or "",
            tax_identifier=vd.get("tax_identifier") or "",
            business_phone=vd.get("business_phone") or "",
            address=vd.get("address") or "",
        )
        output = self.get_serializer(business)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        business = self.get_object()
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            serializer.save()
            return
        if business.owner_id != user.id:
            raise PermissionDenied("Not your business.")
        if business.status not in (BusinessStatus.DRAFT, BusinessStatus.REJECTED):
            raise PermissionDenied(
                "You can only edit verification details while the business is draft "
                "or rejected. Submit for review when ready."
            )
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            instance.delete()
            return
        if instance.owner_id != user.id:
            raise PermissionDenied("Not your business.")
        if instance.status != BusinessStatus.DRAFT:
            raise PermissionDenied("You can only delete a business in draft status.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="submit-for-review")
    @extend_schema(
        tags=["businesses"],
        summary="Submit business for admin verification",
    )
    def submit_for_review(self, request, pk=None):
        business = self.get_object()
        if business.owner_id != request.user.id:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        try:
            submit_business_for_review(business_id=business.pk)
        except BusinessFlowError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        business.refresh_from_db()
        return Response(BusinessSerializer(business).data)

    @action(detail=True, methods=["post"], url_path="approve")
    @extend_schema(
        tags=["businesses"],
        summary="Approve business (admin)",
    )
    def approve(self, request, pk=None):
        try:
            business = approve_business(business_id=self.get_object().pk)
        except BusinessFlowError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BusinessSerializer(business).data)

    @action(detail=True, methods=["post"], url_path="reject")
    @extend_schema(
        request=BusinessRejectSerializer,
        tags=["businesses"],
        summary="Reject business (admin)",
    )
    def reject(self, request, pk=None):
        ser = BusinessRejectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            business = reject_business(
                business_id=self.get_object().pk,
                reason=ser.validated_data["reason"],
            )
        except BusinessFlowError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BusinessSerializer(business).data)
