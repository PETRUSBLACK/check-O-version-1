from rest_framework import serializers

from apps.businesses.models import BusinessMember


class BusinessMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    business_name = serializers.CharField(
        source="business.name",
        read_only=True,
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    class Meta:
        model = BusinessMember

        fields = (
            "id",
            "business",
            "business_name",
            "branch",
            "branch_name",
            "user",
            "user_email",
            "role",
            "is_active",
            "joined_at",
            "invited_by",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "joined_at",
            "created_at",
            "updated_at",
        )