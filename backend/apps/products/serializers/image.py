"""
Product image serializer.

A note on the booleans, because this cost real debugging time:

Photos arrive as multipart/form-data — that's the only way to send a file. DRF
treats multipart as "HTML form input", and for a BooleanField that means an
absent field becomes **False**, not the model default (see
`BooleanField.default_empty_html` in DRF 3.18). So an app that uploaded a photo
without mentioning `is_active` got a photo stamped inactive: HTTP 201, saved to
disk, and never displayed anywhere, with nothing to suggest why.

`FormBoolean` below keeps the declared default when a form leaves the field out,
which is what every caller actually expects.
"""

from rest_framework import serializers
from rest_framework.fields import empty

from apps.products.models import ProductImage


class FormBoolean(serializers.BooleanField):
    """A boolean that keeps its default when multipart data omits it."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # DRF hard-codes this to False for HTML input. Honour the default instead.
        self.default_empty_html = kwargs.get("default", empty)


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for product images.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    business = serializers.UUIDField(
        source="product.business.id",
        read_only=True,
    )

    # A photo is visible unless the vendor hides it, and is not the cover unless
    # the vendor says so.
    is_active = FormBoolean(default=True)
    is_cover = FormBoolean(default=False)

    class Meta:
        model = ProductImage

        fields = (
            "id",
            "product",
            "product_name",
            "business",
            "image",
            "alt_text",
            "is_cover",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "product_name",
            "business",
        )

    def create(self, validated_data):
        """First photo on a product becomes the cover, so nothing is ever coverless."""
        product = validated_data["product"]
        if not product.images.filter(is_active=True).exists():
            validated_data["is_cover"] = True
        image = super().create(validated_data)
        self._settle_cover(image)
        return image

    def update(self, instance, validated_data):
        image = super().update(instance, validated_data)
        self._settle_cover(image)
        return image

    @staticmethod
    def _settle_cover(image: ProductImage) -> None:
        """A product has exactly one cover. Marking a new one demotes the old."""
        if not image.is_cover:
            return
        ProductImage.objects.filter(product_id=image.product_id).exclude(
            pk=image.pk
        ).filter(is_cover=True).update(is_cover=False)
