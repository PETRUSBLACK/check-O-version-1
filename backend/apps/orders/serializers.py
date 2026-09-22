from rest_framework import serializers

from decimal import Decimal

from .models import CheckoutGroup, Order, OrderItem, OrderStatus


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "quantity", "unit_price", "created_at")
        read_only_fields = ("id", "created_at")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True, default=None)

    class Meta:
        model = Order
        fields = (
            "id", "customer", "business", "business_name", "checkout_group",
            "status", "total", "items",
            "fulfilment_type", "paid_at",
            "cancelled_at", "cancelled_by", "cancellation_reason", "cancellation_note",
            "refund_status",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class OrderLineWriteSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    items = OrderLineWriteSerializer(many=True)


class CheckoutGroupSerializer(serializers.ModelSerializer):
    """One checkout: a single payment covering one order per shop."""
    orders = OrderSerializer(many=True, read_only=True)
    order_count = serializers.SerializerMethodField()
    amount_due = serializers.SerializerMethodField()

    class Meta:
        model = CheckoutGroup
        fields = ("id", "customer", "total", "amount_due", "order_count", "orders", "created_at")
        read_only_fields = fields

    def get_order_count(self, obj) -> int:
        return obj.orders.count()

    def get_amount_due(self, obj) -> str:
        """Total of the orders still awaiting payment (cancelled ones are excluded)."""
        due = sum(
            (o.total for o in obj.orders.all() if o.status == OrderStatus.PENDING_PAYMENT),
            Decimal("0.00"),
        )
        return f"{due:.2f}"
