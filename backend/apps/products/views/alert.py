from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from core.permissions import IsVendorOrAdmin
from apps.products.models import InventoryAlert
from apps.products.serializers import InventoryAlertSerializer


@extend_schema_view(
    list=extend_schema(tags=["products"], summary="List inventory alerts"),
    retrieve=extend_schema(tags=["products"], summary="Get inventory alert"),
    create=extend_schema(tags=["products"], summary="Create inventory alert"),
    update=extend_schema(tags=["products"], summary="Update inventory alert"),
    partial_update=extend_schema(tags=["products"], summary="Partially update inventory alert"),
    destroy=extend_schema(tags=["products"], summary="Delete inventory alert"),
)
class InventoryAlertViewSet(viewsets.ModelViewSet):
    """CRUD for product inventory alert records."""

    queryset = InventoryAlert.objects.select_related("product", "product__business")
    serializer_class = InventoryAlertSerializer
    filterset_fields = ("product",)
    search_fields = ("product__name",)
    ordering_fields = ("threshold", "created_at")

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
        alert = self.get_object()
        user = self.request.user

        if (
            not user.is_staff
            and getattr(user, "role", None) != "admin"
            and alert.product.business.owner_id != user.id
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
