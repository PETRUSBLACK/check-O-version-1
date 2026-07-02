from rest_framework import serializers

from apps.businesses.models import Branch


class BranchSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source="business.name",
        read_only=True,
    )

    class Meta:
        model = Branch

        fields = (
            "id",
            "business",
            "business_name",
            "name",
            "branch_code",
            "email",
            "phone_number",
            "manager_name",
            "full_address",
            "city",
            "state",
            "country",
            "postal_code",
            "latitude",
            "longitude",
            "accepts_walk_in",
            "supports_delivery",
            "supports_pickup",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "branch_code",
            "created_at",
            "updated_at",
        )


class BranchCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch

        exclude = (
            "id",
            "branch_code",
            "created_at",
            "updated_at",
        )