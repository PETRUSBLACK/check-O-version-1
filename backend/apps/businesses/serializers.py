from rest_framework import serializers

from .models import Business, BusinessCategory


class BusinessSerializer(serializers.ModelSerializer):
    # Explicitly declared so Swagger marks id as read-only
    # and does not ask for it in the create request form.
    id = serializers.UUIDField(
        read_only=True,
        help_text="Auto-generated UUID. Copy from the create response — required for all subsequent requests.",
    )
    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True,
        help_text="Human-readable category label.",
    )

    class Meta:
        model = Business
        fields = (
            "id",
            "owner",
            "name",
            "slug",
            "category",
            "category_display",
            "status",
            "legal_name",
            "registration_number",
            "tax_identifier",
            "business_phone",
            "address",
            "submitted_for_review_at",
            "verified_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "status",
            "category_display",
            "submitted_for_review_at",
            "verified_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        )


class BusinessCategorySerializer(serializers.Serializer):
    """Returns all available business categories."""
    value = serializers.CharField()
    label = serializers.CharField()


class BusinessRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)
