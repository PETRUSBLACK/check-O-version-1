"""
Product embedding serializer.
"""

from rest_framework import serializers

from apps.products.models import ProductEmbedding


class ProductEmbeddingSerializer(serializers.ModelSerializer):
    """
    Serializer for AI product embeddings.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    class Meta:
        model = ProductEmbedding

        fields = (
            "id",
            "product",
            "product_name",
            "ai_description",
            "keywords",
            "embedding",
            "embedding_model",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "product_name",
        )