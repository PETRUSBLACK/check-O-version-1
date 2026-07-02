from rest_framework import serializers

from .models import Business


class BusinessSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    owner_email = serializers.EmailField(
        source="owner.email",
        read_only=True,
    )

    category_display = serializers.CharField(
        source="get_category_display",
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
            "category_display",
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
            "owner_email",
            "status",
            "created_at",
            "updated_at",
        )


class BusinessCategorySerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class BusinessRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)