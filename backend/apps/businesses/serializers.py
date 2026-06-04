from rest_framework import serializers

from .models import Business


class BusinessSerializer(serializers.ModelSerializer):
    # Explicitly declared so Swagger correctly marks id as read-only
    # and does not ask for it in the create request form.
    id = serializers.UUIDField(
        read_only=True,
        help_text="Auto-generated UUID. Copy this from the create response — required for all subsequent requests.",
    )

    class Meta:
        model = Business
        fields = (
            "id",
            "owner",
            "name",
            "slug",
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
            "submitted_for_review_at",
            "verified_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        )


class BusinessRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)