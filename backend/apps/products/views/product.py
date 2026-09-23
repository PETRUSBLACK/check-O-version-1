from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Prefetch, Q
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.businesses.models import Business
from apps.businesses.choices import BusinessStatus
from core.permissions import IsVendorOrAdmin
from apps.products.models import Product, ProductImage
from apps.products.serializers import ProductSerializer
from apps.products.services.catalog import create_product



@extend_schema_view(
    list=extend_schema(tags=["products"], summary="List products (public sees active from approved shops only)"),
    retrieve=extend_schema(tags=["products"], summary="Get product detail"),
    create=extend_schema(tags=["products"], summary="Create a product (vendor only, business must be approved)"),
    update=extend_schema(tags=["products"], summary="Update a product (vendor — own products only)"),
    partial_update=extend_schema(tags=["products"], summary="Partially update a product"),
    destroy=extend_schema(tags=["products"], summary="Delete a product (vendor — own products only)"),
)
class ProductViewSet(viewsets.ModelViewSet):
    """CRUD: Product catalog management."""
    serializer_class = ProductSerializer
    filterset_fields = ("business", "is_active")
    search_fields = ("name", "description")
    ordering_fields = ("price", "created_at", "name")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsVendorOrAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Product.objects.select_related("business").prefetch_related(
            Prefetch("images", queryset=ProductImage.objects.filter(is_active=True))
        )
        user = self.request.user
        if user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"):
            return qs.all()
        if user.is_authenticated and getattr(user, "role", None) == "vendor":
            # Their own catalogue (including drafts) plus everything a shopper can see —
            # a vendor is also a customer and must be able to browse other shops.
            ids = Business.objects.filter(owner=user).values_list("id", flat=True)
            return qs.filter(
                Q(business_id__in=ids) | Q(is_active=True, business__status="approved")
            ).distinct()
        return qs.filter(is_active=True, business__status="approved")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = serializer.validated_data["business"]
        if not request.user.is_staff and getattr(request.user, "role", None) != "admin":
            if business.owner_id != request.user.id:
                raise PermissionDenied("Not your business.")
            if business.status != BusinessStatus.APPROVED:
                return Response(
                    {"detail": "Business must be approved before you can list products."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        product = create_product(
            business=business,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            price=serializer.validated_data["price"],
            stock=serializer.validated_data.get("stock", 0),
            is_active=serializer.validated_data.get("is_active", True),
        )
        output = self.get_serializer(product)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=self.get_success_headers(output.data))

    def perform_update(self, serializer):
        product = self.get_object()
        user = self.request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if product.business.owner_id != user.id:
                raise PermissionDenied("Not your product.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if instance.business.owner_id != user.id:
                raise PermissionDenied("Not your product.")
        instance.delete()
