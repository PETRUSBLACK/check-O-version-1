"""
Business serializers.

Contains serializers for:
- Listing businesses
- Retrieving business details
- Creating businesses
- Updating businesses
"""

from rest_framework import serializers

from apps.businesses.models import Business
from apps.businesses.services import (
    create_business,
    update_business,
)

class BusinessListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True,
    )

    class Meta:
        model = Business

        fields = (
            "id",
            "name",
            "slug",
            "logo",
            "category",
            "category_display",
            "status",
        )

        read_only_fields = fields

class BusinessDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True,
    )

    class Meta:
        model = Business

        fields = (
            "id",
            "owner",
            "name",
            "slug",
            "category",
            "category_display",
            "tagline",
            "description",
            "logo",
            "cover_image",
            "business_email",
            "business_phone",
            "website",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields



class BusinessCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Business

        fields = (
            "name",
            "category",
            "tagline",
            "description",
            "logo",
            "cover_image",
            "business_email",
            "business_phone",
            "website",
        )

    def validate_name(self, value):
        owner = self.context["request"].user

        if Business.objects.filter(
            owner=owner,
            name__iexact=value,
        ).exists():
            raise serializers.ValidationError(
                "You already have a business with this name."
            )

        return value

    def create(self, validated_data):
        return create_business(
            owner=self.context["request"].user,
            **validated_data,
        )

class BusinessUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Business

        fields = (
            "name",
            "category",
            "tagline",
            "description",
            "logo",
            "cover_image",
            "business_email",
            "business_phone",
            "website",
            "is_active",
        )

    def update(self, instance, validated_data):
        return update_business(
            business=instance,
            **validated_data,
        )