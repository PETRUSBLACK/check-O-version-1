from rest_framework import serializers

from apps.businesses.models import BusinessGallery


class BusinessGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessGallery

        fields = (
            "id",
            "business",
            "image",
            "caption",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )