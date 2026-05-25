from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.ads.serializers import ProductPromotionSerializer
from apps.ads.services.promotion_service import get_featured_products, get_active_discounts


class FeaturedProductsView(APIView):
    """Workflow: Get featured/promoted products for homepage."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["ads"],
        summary="Get featured products",
        description="Returns active featured promotions ordered by boost weight. Optionally filter by city.",
    )
    def get(self, request):
        city = request.query_params.get("city", "")
        limit = min(int(request.query_params.get("limit", 20)), 50)
        promotions = get_featured_products(limit=limit, city=city)
        return Response(ProductPromotionSerializer(promotions, many=True).data)


class ActiveDiscountsView(APIView):
    """Workflow: Get all active discounts and flash sales."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["ads"],
        summary="Get active discounts and flash sales",
        description="Returns all currently active discount/flash sale promotions.",
    )
    def get(self, request):
        discounts = get_active_discounts()
        return Response(ProductPromotionSerializer(discounts, many=True).data)
