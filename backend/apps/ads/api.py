from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import Business
from core.permissions import IsVendorOrAdmin

from .models import ProductPromotion
from .serializers import ProductPromotionSerializer


class ProductPromotionViewSet(viewsets.ModelViewSet):
    queryset = ProductPromotion.objects.all()
    serializer_class = ProductPromotionSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsVendorOrAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        qs = self.queryset.select_related("product__business")
        user = self.request.user
        if self.action in ("list", "retrieve"):
            return qs.order_by("-starts_at")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs.order_by("-starts_at")
        ids = Business.objects.filter(owner=user).values_list("id", flat=True)
        return qs.filter(product__business_id__in=ids).order_by("-starts_at")

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        user = self.request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if product.business.owner_id != user.id:
                raise PermissionDenied("You can only promote your own products.")
        serializer.save()

    def perform_update(self, serializer):
        promo = self.get_object()
        user = self.request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if promo.product.business.owner_id != user.id:
                raise PermissionDenied("Not your promotion.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if instance.product.business.owner_id != user.id:
                raise PermissionDenied("Not your promotion.")
        instance.delete()
