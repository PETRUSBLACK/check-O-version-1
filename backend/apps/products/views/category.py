from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from apps.products.models import ProductCategory
from apps.products.serializers import ProductCategorySerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Product Categories"],
        summary="List product categories",
    ),
    retrieve=extend_schema(
        tags=["Product Categories"],
        summary="Retrieve category",
    ),
    create=extend_schema(
        tags=["Product Categories"],
        summary="Create category",
    ),
    update=extend_schema(
        tags=["Product Categories"],
        summary="Update category",
    ),
    partial_update=extend_schema(
        tags=["Product Categories"],
        summary="Partially update category",
    ),
    destroy=extend_schema(
        tags=["Product Categories"],
        summary="Delete category",
    ),
)
class ProductCategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for product categories.
    """

    queryset = ProductCategory.objects.select_related("parent")

    serializer_class = ProductCategorySerializer

    search_fields = (
        "name",
        "description",
    )

    ordering_fields = (
        "name",
        "display_order",
    )

    lookup_field = "id"

    def get_permissions(self):
        if self.action in (
            "create",
            "update",
            "partial_update",
            "destroy",
        ):
            return [permissions.IsAdminUser()]

        return [permissions.AllowAny()]