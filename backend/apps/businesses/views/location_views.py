from math import asin, cos, radians, sin, sqrt

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.businesses.models import Business, BusinessLocation, BusinessRating, BusinessStatus
from core.permissions import IsCustomer, IsVendor


class BusinessLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessLocation
        fields = ("id", "latitude", "longitude", "city", "state", "country", "full_address")
        read_only_fields = ("id",)


class BusinessRatingSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source="customer.email", read_only=True)

    class Meta:
        model = BusinessRating
        fields = ("id", "score", "review", "customer_email", "created_at")
        read_only_fields = ("id", "customer_email", "created_at")


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Calculate distance between two coordinates in kilometres."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * asin(sqrt(a))


class SetBusinessLocationView(APIView):
    """Workflow: Vendor sets their shop's physical location."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        request=BusinessLocationSerializer,
        responses={200: BusinessLocationSerializer},
        tags=["businesses"],
        summary="Set or update shop location",
    )
    def post(self, request, pk=None):
        business = Business.objects.filter(pk=pk, owner=request.user).first()
        if not business:
            return Response({"detail": "Business not found."}, status=404)

        ser = BusinessLocationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        location, _ = BusinessLocation.objects.update_or_create(
            business=business,
            defaults=ser.validated_data,
        )
        return Response(BusinessLocationSerializer(location).data)


class NearbyShopsView(APIView):
    """
    Workflow: Search for approved shops near a given location.
    Optional: filter by category or product name.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["businesses"],
        summary="Find shops near a location",
        description=(
            "Pass `lat`, `lng`, and optional `radius_km` (default 10), "
            "`category` (e.g. hotel, restaurant, retail), and `product` query params."
        ),
    )
    def get(self, request):
        try:
            lat = float(request.query_params.get("lat", 0))
            lng = float(request.query_params.get("lng", 0))
        except ValueError:
            return Response({"detail": "Invalid lat/lng."}, status=400)

        radius_km = float(request.query_params.get("radius_km", 10))
        product_query = request.query_params.get("product", "").strip()
        category_filter = request.query_params.get("category", "").strip()

        locations = BusinessLocation.objects.select_related(
            "business"
        ).filter(business__status=BusinessStatus.APPROVED)

        # Filter by category if provided
        if category_filter:
            locations = locations.filter(business__category=category_filter)

        results = []
        for loc in locations:
            distance = _haversine_km(lat, lng, loc.latitude, loc.longitude)
            if distance <= radius_km:
                business = loc.business

                # Filter by product name if provided
                if product_query:
                    has_product = business.products.filter(
                        name__icontains=product_query, is_active=True
                    ).exists()
                    if not has_product:
                        continue

                # Calculate average rating
                ratings = list(business.ratings.all())
                avg_rating = (
                    sum(r.score for r in ratings) / len(ratings)
                    if ratings else None
                )

                results.append({
                    "business_id": str(business.pk),
                    "name": business.name,
                    "category": business.category,
                    "category_display": business.get_category_display(),
                    "address": loc.full_address,
                    "city": loc.city,
                    "state": loc.state,
                    "latitude": float(loc.latitude),
                    "longitude": float(loc.longitude),
                    "distance_km": round(distance, 2),
                    "avg_rating": round(avg_rating, 1) if avg_rating else None,
                    "rating_count": len(ratings),
                })

        results.sort(key=lambda x: x["distance_km"])
        return Response(results)


class RateBusinessView(APIView):
    """Workflow: Customer rates a business after a completed order."""
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        request=BusinessRatingSerializer,
        responses={201: BusinessRatingSerializer},
        tags=["businesses"],
        summary="Rate a vendor shop",
    )
    def post(self, request, pk=None):
        business = Business.objects.filter(pk=pk).first()
        if not business:
            return Response({"detail": "Business not found."}, status=404)

        from apps.orders.models import Order, OrderStatus
        has_order = Order.objects.filter(
            customer=request.user,
            status__in=[OrderStatus.DELIVERED.value, OrderStatus.COLLECTED.value],
            items__product__business=business,
        ).exists()
        if not has_order:
            return Response(
                {"detail": "You can only rate a shop after a completed order."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = BusinessRatingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        if ser.validated_data["score"] < 1 or ser.validated_data["score"] > 5:
            return Response({"detail": "Score must be between 1 and 5."}, status=400)

        rating, created = BusinessRating.objects.update_or_create(
            business=business,
            customer=request.user,
            defaults=ser.validated_data,
        )
        return Response(
            BusinessRatingSerializer(rating).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BusinessRatingsView(APIView):
    """CRUD: List all ratings for a business."""
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: BusinessRatingSerializer(many=True)},
        tags=["businesses"],
        summary="List ratings for a shop",
    )
    def get(self, request, pk=None):
        business = Business.objects.filter(pk=pk).first()
        if not business:
            return Response({"detail": "Business not found."}, status=404)
        ratings = BusinessRating.objects.filter(business=business).select_related("customer")
        return Response(BusinessRatingSerializer(ratings, many=True).data)
