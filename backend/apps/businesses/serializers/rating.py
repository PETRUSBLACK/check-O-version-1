from rest_framework import serializers

from apps.businesses.models import BusinessRating


class BusinessRatingSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(
        source="customer.email",
        read_only=True,
    )

    class Meta:
        model = BusinessRating

        fields = (
            "id",
            "business",
            "customer",
            "customer_email",
            "score",
            "review",
            "is_visible",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )