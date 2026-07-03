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
            "is_active",
            "accepts_walk_in",
            "supports_delivery",
            "supports_pickup",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "branch_code",
            "created_at",
            "updated_at",
        )

class BranchListSerializer(serializers.ModelSerializer):
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
            "city",
            "state",
            "is_active",
        )

        read_only_fields = fields


class BranchDetailSerializer(serializers.ModelSerializer):
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
            "created_at",
            "updated_at",
        )


class BranchCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Branch

        fields = (
            "business",
            "name",
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
        )


class BranchUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Branch

        fields = (
            "name",
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
        )

def get_branches():
    """
    Returns all branches.
    """

    return (
        Branch.objects
        .select_related("business")
        .order_by("name")
    )


def get_business_branches(business):
    """
    Returns all branches belonging to a business.
    """

    return (
        Branch.objects
        .filter(business=business)
        .select_related("business")
    )