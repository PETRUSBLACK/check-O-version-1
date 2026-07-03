from rest_framework import serializers

from apps.businesses.models import BusinessDocument


class BusinessDocumentSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source="business.name",
        read_only=True,
    )

    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email",
        read_only=True,
    )

    verified_by_email = serializers.EmailField(
        source="verified_by.email",
        read_only=True,
    )

    has_expired = serializers.ReadOnlyField()

    class Meta:
        model = BusinessDocument

        fields = (
            "id",
            "business",
            "business_name",
            "document_type",
            "title",
            "file",
            "description",
            "uploaded_by",
            "uploaded_by_email",
            "expiry_date",
            "has_expired",
            "is_verified",
            "verified_at",
            "verified_by",
            "verified_by_email",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "uploaded_by",
            "uploaded_by_email",
            "verified_at",
            "verified_by",
            "verified_by_email",
            "is_verified",
            "has_expired",
            "created_at",
            "updated_at",
        )