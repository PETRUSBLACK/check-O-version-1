from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiParameter
from drf_spectacular.openapi import AutoSchema

from core.permissions import IsStaffOrPlatformAdmin, IsVendor
from apps.businesses.models import Business, BusinessStatus
from apps.businesses.serializers import BusinessRejectSerializer, BusinessSerializer
from apps.businesses.services.registration import (
    BusinessFlowError,
    approve_business,
    reject_business,
    register_business,
    submit_business_for_review,
)


@extend_schema_view(
    list=extend_schema(
        tags=["businesses"],
        summary="List businesses",
        description=(
            "Returns a list of businesses. "
            "*Admins/staff* see all businesses regardless of status. "
            "*Vendors* see only their own businesses. "
            "*Customers / unauthenticated* see only approved businesses. "
            "Authenticate via the Authorize button (JWT) to see more results."
        ),
        responses={200: BusinessSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["businesses"],
        summary="Get a business by UUID",
        description="Retrieve full details of a single business. Pass the id (UUID) returned when the business was created.",
        responses={200: BusinessSerializer},
    ),
    update=extend_schema(
        tags=["businesses"],
        summary="Update a business (full)",
        responses={200: BusinessSerializer},
    ),
    partial_update=extend_schema(
        tags=["businesses"],
        summary="Update a business (partial)",
        responses={200: BusinessSerializer},
    ),
    destroy=extend_schema(
        tags=["businesses"],
        summary="Delete a business (draft only)",
        responses={204: OpenApiResponse(description="Deleted successfully")},
    ),
)
class BusinessViewSet(viewsets.ModelViewSet):
    """CRUD: Business management."""
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

    @extend_schema(
        tags=["businesses"],
        summary="Register a new business",
        description=(
            "Creates a new business in *draft* status. "
            "The response includes the business id (UUID) — *copy this value*, "
            "you will need it for all subsequent requests such as submitting for review, "
            "setting a location, or managing products.\n\n"
            "Requires a *Vendor* role JWT token."
        ),
        request=BusinessSerializer,
        responses={
            201: OpenApiResponse(
                response=BusinessSerializer,
                description="Business created. The id field is the UUID to use in all future requests.",
            ),
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Only vendors can register a business"),
        },
    )
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
            raise PermissionDenied("You can only edit while draft or rejected.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            instance.delete()
            return
        if instance.owner_id != user.id:
            raise PermissionDenied("Not your business.")
        if instance.status != BusinessStatus.DRAFT:
            raise PermissionDenied("You can only delete a draft business.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="submit-for-review")
    @extend_schema(
        tags=["businesses"],
        summary="Submit business for admin verification",
        description="Moves the business from *draft* to *pending* status. Use the business id (UUID) in the URL.",
        responses={
            200: OpenApiResponse(response=BusinessSerializer, description="Submitted successfully"),
            400: OpenApiResponse(description="Business is not in a submittable state"),
            403: OpenApiResponse(description="You can only submit your own business"),
        },
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
        summary="Approve business (admin only)",
        description="Approves a pending business. Requires admin/staff role.",
        responses={
            200: OpenApiResponse(response=BusinessSerializer, description="Business approved"),
            400: OpenApiResponse(description="Business is not in pending state"),
        },
    )
    def approve(self, request, pk=None):
        try:
            business = approve_business(business_id=self.get_object().pk)
        except BusinessFlowError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BusinessSerializer(business).data)

    @action(detail=True, methods=["post"], url_path="reject")
    @extend_schema(
        tags=["businesses"],
        summary="Reject business (admin only)",
        description="Rejects a pending business with a reason. Requires admin/staff role.",
        request=BusinessRejectSerializer,
        responses={
            200: OpenApiResponse(response=BusinessSerializer, description="Business rejected"),
            400: OpenApiResponse(description="Business is not in pending state"),
        },
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