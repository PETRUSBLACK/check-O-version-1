from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import CheckoutGroup
from apps.orders.serializers import CheckoutGroupSerializer


class CheckoutGroupDetailView(APIView):
    """Read: one checkout (single payment) and its per-shop orders."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: CheckoutGroupSerializer},
        tags=["orders"],
        summary="Get a checkout and its shop orders",
    )
    def get(self, request, pk=None):
        group = (
            CheckoutGroup.objects.filter(pk=pk, customer=request.user)
            .prefetch_related("orders__items__product", "orders__business")
            .first()
        )
        if not group:
            return Response({"detail": "Checkout not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CheckoutGroupSerializer(group).data)
