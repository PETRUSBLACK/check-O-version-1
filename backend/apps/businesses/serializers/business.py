from rest_framework import serializers

from apps.businesses.models import Business


class BusinessSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(
        source="owner.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Business

        fields = (
            "id",
            "owner",
            "owner_name",
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
            "status",
            "created_at",
            "updated_at",
        )


class BusinessCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business

        exclude = (
            "owner",
            "status",
            "slug",
        )

    def create(self, validated_data):
        user = self.context["request"].user

        from apps.businesses.services import create_business

        return create_business(
            owner=user,
            **validated_data,
        )


class BusinessUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business

        exclude = (
            "owner",
            "status",
            "slug",
        )

    def update(self, instance, validated_data):
        from apps.businesses.services import update_business

        return update_business(
            business=instance,
            **validated_data,
        )