from rest_framework import serializers

from .models import Menu, MenuSection, MenuItem, Reservation, DietaryFlag


class MenuItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = MenuItem
        fields = (
            "id",
            "name",
            "description",
            "price",
            "image",
            "is_available",
            "dietary_flags",
            "preparation_minutes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_dietary_flags(self, value):
        valid = {c[0] for c in DietaryFlag.choices}
        invalid = [f for f in value if f not in valid]
        if invalid:
            raise serializers.ValidationError(
                f"Invalid dietary flags: {invalid}. Valid options: {list(valid)}"
            )
        return value


class MenuSectionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = MenuSection
        fields = ("id", "name", "position", "items")
        read_only_fields = ("id",)


class MenuSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    sections = MenuSectionSerializer(many=True, read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)

    class Meta:
        model = Menu
        fields = (
            "id",
            "business",
            "business_name",
            "name",
            "description",
            "is_active",
            "sections",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "business", "business_name", "created_at", "updated_at")


class ReservationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)

    class Meta:
        model = Reservation
        fields = (
            "id",
            "business",
            "business_name",
            "customer",
            "customer_email",
            "date",
            "time",
            "party_size",
            "status",
            "special_requests",
            "rejection_reason",
            "confirmed_at",
            "cancelled_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "business_name",
            "customer",
            "customer_email",
            "status",
            "rejection_reason",
            "confirmed_at",
            "cancelled_at",
            "created_at",
            "updated_at",
        )

    def validate_party_size(self, value):
        if value < 1:
            raise serializers.ValidationError("Party size must be at least 1.")
        if value > 50:
            raise serializers.ValidationError("Party size cannot exceed 50.")
        return value


class ReservationConfirmSerializer(serializers.Serializer):
    """Used by vendor to confirm a reservation."""
    pass


class ReservationRejectSerializer(serializers.Serializer):
    """Used by vendor to reject a reservation."""
    reason = serializers.CharField(max_length=500)


class DietaryFlagSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
