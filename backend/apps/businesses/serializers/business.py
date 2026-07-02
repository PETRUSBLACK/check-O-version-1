from rest_framework import serializers

from apps.businesses.models import Business


class BusinessSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(
        source="owner.email",
        read_only=True,
    )

    class Meta:
        model = Business

        fields = (
            "id",
            "owner",
            "owner_email",
            "name",
            "slug",
            "category",
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

        read_only_fields = (
            "id",
            "owner",
            "slug",
            "status",
            "created_at",
            "updated_at",
        )


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