from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from core.permissions import IsVendorOrAdmin
from apps.products.models import ProductEmbedding
from apps.products.serializers import ProductEmbeddingSerializer


@extend_schema_view(
    list=extend_schema(tags=["products"], summary="List product embeddings"),
    retrieve=extend_schema(tags=["products"], summary="Get product embedding"),
    create=extend_schema(tags=["products"], summary="Create product embedding"),
    update=extend_schema(tags=["products"], summary="Update product embedding"),
    partial_update=extend_schema(tags=["products"], summary="Partially update product embedding"),
    destroy=extend_schema(tags=["products"], summary="Delete product embedding"),
)
class ProductEmbeddingViewSet(viewsets.ModelViewSet):
    """CRUD for AI embeddings associated with products."""

    queryset = ProductEmbedding.objects.select_related("product", "product__business")
    serializer_class = ProductEmbeddingSerializer
    filterset_fields = ("product",)
    search_fields = ("product__name", "ai_description")
    ordering_fields = ("created_at", "embedding_model")

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
        embedding = self.get_object()
        user = self.request.user

        if (
            not user.is_staff
            and getattr(user, "role", None) != "admin"
            and embedding.product.business.owner_id != user.id
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
