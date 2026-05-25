from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from drf_spectacular.utils import extend_schema

from apps.cart.serializers import CartItemSerializer, CartSerializer
from apps.cart.services.cart_service import CartError, get_or_create_cart, remove_from_cart


class CartViewSet(ViewSet):
    """CRUD: View and manage the customer's cart."""
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CartSerializer}, tags=["cart"], summary="Get current user's cart")
    def list(self, request):
        cart = get_or_create_cart(customer=request.user)
        return Response(CartSerializer(cart).data)

    @extend_schema(
        request=None,
        responses={204: None},
        tags=["cart"],
        summary="Clear all items from cart",
    )
    def destroy(self, request, pk=None):
        from apps.cart.services.cart_service import clear_cart
        clear_cart(customer=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
