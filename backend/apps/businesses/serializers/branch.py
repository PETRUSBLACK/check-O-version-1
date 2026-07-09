"""
Branch serializers.

Contains serializers for:
- Listing branches
- Retrieving branch details
- Creating branches
- Updating branches
"""

from rest_framework import serializers

from apps.businesses.models import Branch
from apps.businesses.services import (
    create_branch,
    update_branch,
)


class BranchListSerializer(serializers.ModelSerializer):
    """
    Serializer used when listing branches.
    """

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
    """
    Serializer used when retrieving a single branch.
    """

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
    """
    Serializer used for creating a branch.
    """

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
        )

    def create(self, validated_data):
        """
        Delegate branch creation to the service layer.
        """

        return create_branch(
            business=self.context["business"],
            **validated_data,
        )


class BranchUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer used for updating a branch.
    """

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

    def update(self, instance, validated_data):
        """
        Delegate branch updates to the service layer.
        """

        return update_branch(
            branch=instance,
            **validated_data,
        )