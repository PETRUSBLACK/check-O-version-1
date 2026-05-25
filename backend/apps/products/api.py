from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.businesses.models import Business, BusinessStatus
from core.permissions import IsVendorOrAdmin

from .models import Product
from .serializers import ProductSerializer
from .services.catalog import create_product


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    filterset_fields = ("business", "is_active")
    search_fields = ("name", "description")
    ordering_fields = ("price", "created_at", "name")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsVendorOrAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Product.objects.select_related("business")
        user = self.request.user
        if user.is_authenticated and (
            user.is_staff or getattr(user, "role", None) == "admin"
        ):
            return qs.all()
        if user.is_authenticated and getattr(user, "role", None) == "vendor":
            ids = Business.objects.filter(owner=user).values_list("id", flat=True)
            return qs.filter(business_id__in=ids)
        return qs.filter(is_active=True, business__status="approved")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = serializer.validated_data["business"]
        if (
            not request.user.is_staff
            and getattr(request.user, "role", None) != "admin"
            and business.owner_id != request.user.id
        ):
            raise permissions.PermissionDenied("Not your business.")
        if business.status != BusinessStatus.APPROVED:
            if not (
                request.user.is_staff
                or getattr(request.user, "role", None) == "admin"
            ):
                return Response(
                    {
                        "detail": "Business must be approved by the platform before "
                        "you can list products. Complete verification and wait for approval."
                    },
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
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

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
