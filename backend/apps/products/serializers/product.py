from rest_framework import serializers

from apps.products.models import Product

# Numbers only the shop owner (or an admin) is allowed to see.
# cost_price in particular reveals the shop's profit margin.
VENDOR_ONLY_FIELDS = (
    "cost_price",
    "stock",
    "smartmall_allocation",
    "low_stock_threshold",
)


class ProductSerializer(serializers.ModelSerializer):
    available_stock = serializers.SerializerMethodField()
    uses_channel_allocation = serializers.SerializerMethodField()
    business_name = serializers.CharField(source="business.name", read_only=True)
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = (
            "id",
            "business",
            "business_name",
            "category",
            "cover_image",
            "name",
            "slug",
            "sku",
            "barcode",
            "description",
            "currency",
            "cost_price",
            "price",
            "stock",
            "smartmall_allocation",
            "available_stock",
            "uses_channel_allocation",
            "low_stock_threshold",
            "is_active",
            "is_featured",
            "is_published",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
        )

    def get_available_stock(self, obj) -> int:
        # The model owns this rule (min of stock and allocation) — don't repeat it here.
        return obj.available_stock

    def get_uses_channel_allocation(self, obj) -> bool:
        return obj.uses_channel_allocation

    def get_cover_image(self, obj) -> str | None:
        """
        The photo to show in a list or on the product page: the one the vendor marked
        as cover, otherwise the first active one. Returns a full URL the app can load.
        """
        images = getattr(obj, "images", None)
        if images is None:
            return None
        chosen = None
        # Use the already-loaded list when the view prefetched it, so a grid of
        # products is still one query.
        loaded = getattr(images, "_result_cache", None)
        candidates = loaded if loaded is not None else list(images.filter(is_active=True))
        for image in candidates:
            if not image.is_active:
                continue
            if image.is_cover:
                chosen = image
                break
            if chosen is None:
                chosen = image
        if chosen is None or not chosen.image:
            return None
        request = self.context.get("request")
        url = chosen.image.url
        return request.build_absolute_uri(url) if request else url

    def _may_see_private_fields(self, obj) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        if user.is_staff or getattr(user, "role", None) == "admin":
            return True
        return obj.business_id in _owned_business_ids(user)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self._may_see_private_fields(instance):
            for field in VENDOR_ONLY_FIELDS:
                data.pop(field, None)
        return data


def _owned_business_ids(user) -> set:
    """The businesses this user owns, looked up once per request."""
    cached = getattr(user, "_owned_business_ids", None)
    if cached is None:
        from apps.businesses.models import Business

        cached = set(Business.objects.filter(owner=user).values_list("id", flat=True))
        user._owned_business_ids = cached
    return cached
