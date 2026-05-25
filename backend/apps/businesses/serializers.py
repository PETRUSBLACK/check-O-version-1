from rest_framework import serializers

from .models import Business


class BusinessSerializer(serializers.ModelSerializer):
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
