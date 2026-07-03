from rest_framework import serializers

from apps.businesses.models import BusinessVerification


class BusinessVerificationSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source="business.name",
        read_only=True,
    )

    verified_by_email = serializers.EmailField(
        source="verified_by.email",
        read_only=True,
    )

    class Meta:
        model = BusinessVerification

        fields = (
            "id",
            "business",
            "business_name",
            "legal_name",
            "registration_number",
            "tax_identifier",
            "status",
            "submitted_at",
            "verified_at",
            "verified_by",
            "verified_by_email",
            "rejection_reason",
            "notes",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "status",
            "submitted_at",
            "verified_at",
            "verified_by",
            "verified_by_email",
            "created_at",
            "updated_at",
        )