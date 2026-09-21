from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "quantity", "unit_price", "created_at")
        read_only_fields = ("id", "created_at")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "customer", "status", "total", "items",
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
