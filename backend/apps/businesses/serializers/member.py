"""
Business member serializers.
"""

from rest_framework import serializers

from apps.businesses.models import BusinessMember
from apps.businesses.services import (
    create_member,
    update_member,
)


class BusinessMemberListSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source="business.name",
        read_only=True,
    )

    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    role_display = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    class Meta:
        model = BusinessMember

        fields = (
            "id",
            "business",
            "business_name",
            "user",
            "user_email",
            "role",
            "role_display",
            "status",
            "joined_at",
        )

        read_only_fields = fields     


class BusinessMemberDetailSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        source="business.name",
        read_only=True,
    )

    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    role_display = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = BusinessMember

        fields = (
            "id",
            "business",
            "business_name",
            "branch",
            "user",
            "user_email",
            "role",
            "role_display",
            "job_title",
            "status",
            "status_display",
            "joined_at",
            "left_at",
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


class BusinessMemberCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = BusinessMember

        fields = (
            "business",
            "branch",
            "user",
            "role",
            "job_title",
            "status",
        )

    def validate(self, attrs):
        business = attrs["business"]
        user = attrs["user"]

        if BusinessMember.objects.filter(
            business=business,
            user=user,
        ).exists():
            raise serializers.ValidationError(
                "This user is already a member of the business."
            )

        return attrs

    def create(self, validated_data):
        return create_member(
            invited_by=self.context["request"].user,
            **validated_data,
        )

class BusinessMemberUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = BusinessMember

        fields = (
            "branch",
            "role",
            "job_title",
            "status",
        )

    def update(self, instance, validated_data):
        return update_member(
            member=instance,
            **validated_data,
        )