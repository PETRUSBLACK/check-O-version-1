from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.cart.serializers import (
    AddToCartSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)
from apps.cart.services.cart_service import (
    CartError,
    add_to_cart,
    checkout,
    get_or_create_cart,
    remove_from_cart,
    update_cart_item,
)
from apps.orders.serializers import OrderSerializer
from core.permissions import IsCustomer


class AddToCartView(APIView):
    """Workflow: Add a product to the cart (or increment quantity)."""
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        request=AddToCartSerializer,
        responses={200: CartSerializer},
        tags=["cart"],
        summary="Add product to cart",
    )
    def post(self, request):
        ser = AddToCartSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            add_to_cart(
                customer=request.user,
                product_id=ser.validated_data["product_id"],
                quantity=ser.validated_data["quantity"],
            )
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_cart(customer=request.user)
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class UpdateCartItemView(APIView):
    """Workflow: Set exact quantity of a cart item (0 = remove)."""
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        request=UpdateCartItemSerializer,
        responses={200: CartSerializer},
        tags=["cart"],
        summary="Update cart item quantity (0 removes the item)",
    )
    def patch(self, request):
        ser = UpdateCartItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            update_cart_item(
                customer=request.user,
                product_id=ser.validated_data["product_id"],
                quantity=ser.validated_data["quantity"],
            )
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_cart(customer=request.user)
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class RemoveFromCartView(APIView):
    """Workflow: Remove a specific product from the cart."""
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        responses={200: CartSerializer},
        tags=["cart"],
        summary="Remove a product from cart",
    )
    def delete(self, request, product_id):
        try:
            remove_from_cart(customer=request.user, product_id=product_id)
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_cart(customer=request.user)
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class CheckoutView(APIView):
    """
    Workflow: Convert cart into a confirmed Order.

    Full checkout flow:
      Cart → validate stock → deduct stock → create Order → clear Cart

    Returns the created Order. Customer must then initiate payment.
    """
    permission_classes = [IsAuthenticated, IsCustomer]

    @extend_schema(
        request=None,
        responses={201: OrderSerializer},
        tags=["cart"],
        summary="Checkout: convert cart into an order",
        description=(
            "Converts the current cart into an Order with status `pending_payment`. "
            "Stock is reserved immediately. Cart is cleared after successful checkout. "
            "Call `POST /api/payments/initiate/` next to pay for the order."
        ),
    )
    def post(self, request):
        try:
            order = checkout(customer=request.user)
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
