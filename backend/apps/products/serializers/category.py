from rest_framework import serializers

from apps.products.models import ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "parent",
            "display_order",
            "is_active",
            "children_count",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "children_count",
        )

    def get_children_count(self, obj):
        return obj.children.count()