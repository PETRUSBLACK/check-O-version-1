"""
Product image ViewSet.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from core.permissions import IsVendorOrAdmin
from apps.products.models import ProductImage
from apps.products.serializers.image import ProductImageSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Product Images"],
        summary="List product images",
    ),
    retrieve=extend_schema(
        tags=["Product Images"],
        summary="Retrieve product image",
    ),
    create=extend_schema(
        tags=["Product Images"],
        summary="Upload product image",
    ),
    update=extend_schema(
        tags=["Product Images"],
        summary="Update product image",
    ),
    partial_update=extend_schema(
        tags=["Product Images"],
        summary="Partially update product image",
    ),
    destroy=extend_schema(
        tags=["Product Images"],
        summary="Delete product image",
    ),
)
class ProductImageViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for product images.
    """

    queryset = ProductImage.objects.select_related(
        "product",
        "product__business",
    )

    serializer_class = ProductImageSerializer

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filterset_fields = (
        "product",
        "is_cover",
        "is_active",
    )

    ordering_fields = (
        "display_order",
        "created_at",
    )

    search_fields = (
        "alt_text",
        "product__name",
    )

    def get_permissions(self):
        if self.action in (
            "create",
            "update",
            "partial_update",
            "destroy",
        ):
            return [
                permissions.IsAuthenticated(),
                IsVendorOrAdmin(),
            ]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        user = self.request.user

        if (
            not user.is_staff
            and getattr(user, "role", None) != "admin"
            and product.business.owner_id != user.id
        ):
            raise PermissionDenied(
                "You do not own this product."
            )

        serializer.save()

    def perform_update(self, serializer):
        image = self.get_object()
        user = self.request.user

        if (
            not user.is_staff
            and getattr(user, "role", None) != "admin"
            and image.product.business.owner_id != user.id
        ):
            raise PermissionDenied(
                "You do not own this product."
            )

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if (
            not user.is_staff
            and getattr(user, "role", None) != "admin"
            and instance.product.business.owner_id != user.id
        ):
            raise PermissionDenied(
                "You do not own this product."
            )

        instance.delete()