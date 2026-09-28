from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.products.serializers import ProductSerializer
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "product_id",
            "quantity",
            "line_total",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CartShopSerializer(serializers.Serializer):
    """A shop represented in the cart, with what it can do about delivery."""
    id = serializers.UUIDField()
    name = serializers.CharField()
    delivers = serializers.BooleanField()
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    shops = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "items",
            "shops",
            "total",
            "item_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    @extend_schema_field(CartShopSerializer(many=True))
    def get_shops(self, obj):
        """
        One entry per shop in the cart, so the checkout screen can offer delivery
        or pickup per shop without a round trip for each one.
        """
        seen = {}
        for item in obj.items.all():
            business = item.product.business
            if business.id in seen:
                continue
            seen[business.id] = {
                "id": business.id,
                "name": business.name,
                "delivers": business.delivers,
                "delivery_fee": business.delivery_fee,
            }
        return CartShopSerializer(list(seen.values()), many=True).data


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateCartItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=0)


class DeliveryDetailsSerializer(serializers.Serializer):
    """Where a delivered order is going. Only needed if a shop is delivering."""
    recipient_name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=32)
    address = serializers.CharField()


class CheckoutSerializer(serializers.Serializer):
    """
    `fulfilment` maps each shop id to "delivery" or "pickup". Shops left out fall
    back to delivery when that shop delivers, otherwise pickup.
    """
    fulfilment = serializers.DictField(
        child=serializers.ChoiceField(choices=["delivery", "pickup"]),
        required=False,
    )
    delivery = DeliveryDetailsSerializer(required=False)
