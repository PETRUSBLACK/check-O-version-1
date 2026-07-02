from rest_framework import serializers

from apps.businesses.models import BusinessVerification


class BusinessVerificationSerializer(serializers.ModelSerializer):
    verified_by_email = serializers.EmailField(
        source="verified_by.email",
        read_only=True,
    )

    class Meta:
        model = BusinessVerification

        fields = "__all__"

        read_only_fields = (
            "id",
            "verified_at",
            "verified_by",
            "created_at",
            "updated_at",
        )