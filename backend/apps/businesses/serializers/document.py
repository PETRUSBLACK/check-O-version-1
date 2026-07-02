from rest_framework import serializers

from apps.businesses.models import BusinessDocument


class BusinessDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email",
        read_only=True,
    )

    verified_by_email = serializers.EmailField(
        source="verified_by.email",
        read_only=True,
    )

    class Meta:
        model = BusinessDocument

        fields = "__all__"

        read_only_fields = (
            "id",
            "is_verified",
            "verified_at",
            "verified_by",
            "created_at",
            "updated_at",
        )