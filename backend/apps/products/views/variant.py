from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from core.permissions import IsVendorOrAdmin
from apps.products.models import ProductVariant
from apps.products.serializers import ProductVariantSerializer


@extend_schema_view(
    list=extend_schema(tags=["products"], summary="List product variants"),
    retrieve=extend_schema(tags=["products"], summary="Get product variant"),
    create=extend_schema(tags=["products"], summary="Create a product variant"),
    update=extend_schema(tags=["products"], summary="Update a product variant"),
    partial_update=extend_schema(tags=["products"], summary="Partially update a product variant"),
    destroy=extend_schema(tags=["products"], summary="Delete a product variant"),
)
class ProductVariantViewSet(viewsets.ModelViewSet):
    """CRUD for product variants."""

    queryset = ProductVariant.objects.select_related("product", "product__business")
    serializer_class = ProductVariantSerializer
    filterset_fields = ("product", "is_active")
    search_fields = ("name", "value", "product__name")
    ordering_fields = ("name", "price_adjustment", "stock", "created_at")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsVendorOrAdmin()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        user = self.request.user

        if (
            not user.is_staff
            and getattr(user, "role", None) != "admin"
            and product.business.owner_id != user.id
        ):
            raise PermissionDenied("You do not own this product.")

        serializer.save()

    def perform_update(self, serializer):
        variant = self.get_object()
        user = self.request.user

        if (
            not user.is_staff
            and getattr(user, "role", None) != "admin"
            and variant.product.business.owner_id != user.id
        ):
            raise PermissionDenied("You do not own this product.")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if (
            not user.is_staff
            and getattr(user, "role", None) != "admin"
            and instance.product.business.owner_id != user.id
        ):
            raise PermissionDenied("You do not own this product.")

        instance.delete()
