from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.businesses.models import Business
from core.permissions import IsVendorOrAdmin
from apps.ads.models import ProductPromotion
from apps.ads.serializers import ProductPromotionSerializer
from apps.ads.services.promotion_service import PromotionError, create_promotion, deactivate_promotion


@extend_schema_view(
    list=extend_schema(tags=["ads"], summary="List promotions"),
    retrieve=extend_schema(tags=["ads"], summary="Get promotion detail"),
)
class ProductPromotionViewSet(viewsets.ModelViewSet):
    """CRUD: Product promotion management."""
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
            return qs.order_by("-boost_weight", "-starts_at")
        if not user.is_authenticated:
            return qs.none()
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs.order_by("-starts_at")
        ids = Business.objects.filter(owner=user).values_list("id", flat=True)
        return qs.filter(product__business_id__in=ids).order_by("-starts_at")

    @extend_schema(tags=["ads"], summary="Create a product promotion")
    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        product = ser.validated_data["product"]
        user = request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if product.business.owner_id != user.id:
                raise PermissionDenied("You can only promote your own products.")
        try:
            promotion = create_promotion(
                product=product,
                title=ser.validated_data["title"],
                promotion_type=ser.validated_data.get("promotion_type", "featured"),
                starts_at=ser.validated_data["starts_at"],
                ends_at=ser.validated_data["ends_at"],
                boost_weight=ser.validated_data.get("boost_weight", 1),
                discount_percent=ser.validated_data.get("discount_percent", 0),
                budget=ser.validated_data.get("budget", 0),
            )
        except PromotionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(promotion).data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=["ads"], summary="Deactivate a promotion")
    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        promotion = self.get_object()
        user = request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if promotion.product.business.owner_id != user.id:
                raise PermissionDenied("Not your promotion.")
        promotion = deactivate_promotion(promotion_id=promotion.pk)
        return Response(self.get_serializer(promotion).data)
