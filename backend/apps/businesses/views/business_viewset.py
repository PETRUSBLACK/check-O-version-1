from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from core.permissions import IsStaffOrPlatformAdmin, IsVendor
from apps.businesses.models import Business, BusinessCategory, BusinessStatus
from apps.businesses.serializers import (
    BusinessCategorySerializer,
    BusinessRejectSerializer,
    BusinessSerializer,
)
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
            "**Admins/staff** see all businesses. "
            "**Vendors** see only their own. "
            "**Customers / unauthenticated** see only approved businesses. "
            "Filter by category using `?category=hotel`, `?category=restaurant`, etc."
        ),
        responses={200: BusinessSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["businesses"],
        summary="Get a business by UUID",
        responses={200: BusinessSerializer},
    ),
    update=extend_schema(tags=["businesses"], summary="Update a business (full)", responses={200: BusinessSerializer}),
    partial_update=extend_schema(tags=["businesses"], summary="Update a business (partial)", responses={200: BusinessSerializer}),
    destroy=extend_schema(tags=["businesses"], summary="Delete a business (draft only)"),
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
            qs = qs.filter(status=BusinessStatus.APPROVED)
        elif user.is_staff or getattr(user, "role", None) == "admin":
            pass  # see all
        elif getattr(user, "role", None) == "vendor":
            qs = qs.filter(owner=user)
        else:
            qs = qs.filter(status=BusinessStatus.APPROVED)

        # Filter by category if provided
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)

        return qs

    @extend_schema(
        tags=["businesses"],
        summary="Register a new business",
        description=(
            "Creates a new business in **draft** status. "
            "The `id` (UUID) in the response is required for all subsequent requests. "
            "Choose a `category` from: retail, grocery, restaurant, hotel, pharmacy, "
            "fashion, electronics, beauty, health, education, automobile, other."
        ),
        request=BusinessSerializer,
        responses={
            201: OpenApiResponse(
                response=BusinessSerializer,
                description="Business created. Copy the `id` UUID from this response.",
            ),
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Vendor role required"),
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
            category=vd.get("category") or BusinessCategory.RETAIL,
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

    @action(detail=False, methods=["get"], url_path="categories", permission_classes=[permissions.AllowAny])
    @extend_schema(
        tags=["businesses"],
        summary="List all business categories",
        description="Returns all available categories a vendor can register under.",
        responses={200: BusinessCategorySerializer(many=True)},
    )
    def categories(self, request):
        """Returns all available business categories."""
        data = [
            {"value": value, "label": label}
            for value, label in BusinessCategory.choices
        ]
        return Response(data)

    @action(detail=True, methods=["post"], url_path="submit-for-review")
    @extend_schema(
        tags=["businesses"],
        summary="Submit business for admin verification",
        responses={
            200: OpenApiResponse(response=BusinessSerializer, description="Submitted successfully"),
            400: OpenApiResponse(description="Missing required fields or invalid state"),
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
        responses={200: OpenApiResponse(response=BusinessSerializer, description="Approved")},
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
        request=BusinessRejectSerializer,
        responses={200: OpenApiResponse(response=BusinessSerializer, description="Rejected")},
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
