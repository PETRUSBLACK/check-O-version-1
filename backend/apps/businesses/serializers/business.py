"""
Business serializers.

Contains serializers for:
- Listing businesses
- Retrieving business details
- Creating businesses
- Updating businesses
"""

from rest_framework import serializers

from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.businesses.services import (
    create_business,
    update_business,
)
from apps.businesses.services.registration import missing_before_review

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

    avg_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    display_address = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    missing_before_review = serializers.SerializerMethodField()

    def get_latitude(self, obj) -> float | None:
        location = getattr(obj, "location", None)
        return float(location.latitude) if location is not None else None

    def get_longitude(self, obj) -> float | None:
        location = getattr(obj, "location", None)
        return float(location.longitude) if location is not None else None

    def get_missing_before_review(self, obj) -> list[str]:
        """
        What this shop still has to fill in before it can be submitted, in the
        vendor's own words. The My shop screen prints it as a checklist.

        Only the owner and staff get it, and only while the shop is not approved
        yet. An approved shop has nothing outstanding by definition, and working
        the list out costs a query — no reason to spend it on every shop page a
        shopper opens.
        """
        if obj.status == BusinessStatus.APPROVED:
            return []

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return []
        if obj.owner_id != user.id and not (
            user.is_staff or getattr(user, "role", None) == "admin"
        ):
            return []
        return missing_before_review(obj)

    def get_avg_rating(self, obj) -> float | None:
        scores = [r.score for r in obj.ratings.all()]
        return round(sum(scores) / len(scores), 1) if scores else None

    def get_rating_count(self, obj) -> int:
        return len(obj.ratings.all())

    def get_display_address(self, obj) -> str:
        """
        The one address to show a customer — "where is this shop?"

        There are two in the database and vendors rarely fill both. `Business.address`
        is typed on the business form and is often left blank. The location row's
        address is the one that carries the GPS used for distance, so it is the more
        reliable of the two and it includes the city.

        Prefer the location, fall back to the business field, and return "" rather
        than None so the app never prints "null" at someone.
        """
        location = getattr(obj, "location", None)
        if location is not None and (location.address or "").strip():
            parts = [location.address.strip()]
            # Don't repeat "Asaba" when the street line already says it.
            for extra in (location.city, location.state):
                if extra and extra.strip() and extra.strip().lower() not in parts[0].lower():
                    parts.append(extra.strip())
            return ", ".join(parts)
        return (obj.address or "").strip()

    class Meta:
        model = Business

        fields = (
            "id",
            "owner",
            "name",
            "slug",
            "category",
            "category_display",
            "avg_rating",
            "rating_count",
            "delivers",
            "delivery_fee",
            "tagline",
            "description",
            "logo",
            "cover_image",
            "business_email",
            "business_phone",
            "website",
            "legal_name",
            "registration_number",
            "address",
            "display_address",
            "latitude",
            "longitude",
            "missing_before_review",
            "submitted_for_review_at",
            "verified_at",
            "rejection_reason",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields



class BusinessCreateSerializer(serializers.ModelSerializer):
    """
    Signing a shop up. Only a name and a category are required: a trader in
    Ogbeogonogo market has no CAC certificate, and asking for one at the door
    would end Check-O's vendor list at about three shops.

    `slug` may be left out — Business.save() builds a unique one from the name,
    so nobody has to invent a web address for their own shop. Delivery is here
    too, so the app can create a complete shop in one request instead of
    creating it and then immediately patching it.
    """

    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Business

        fields = (
            "id",
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
            "legal_name",
            "registration_number",
            "address",
            "delivers",
            "delivery_fee",
        )

        read_only_fields = ("id",)

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

    def validate_slug(self, value):
        # Blank means "work it out from the name", which save() does.
        if value and Business.objects.filter(slug__iexact=value).exists():
            raise serializers.ValidationError("A business with this slug already exists.")

        return value

    def create(self, validated_data):
        return create_business(
            owner=self.context["request"].user,
            **validated_data,
        )

# What a shop was approved *as*. A shop reviewed and approved as "Mama Ngozi
# Provisions, a retail store" must not quietly become a pharmacy afterwards, so
# these stop being the vendor's to change once a human has signed them off.
# Everything else — phone, address, description, logo, delivery fee — is the
# shop's own business and changes all the time. The old rule refused *every*
# edit after approval, which meant an approved vendor could not correct their
# own phone number or put their delivery fee up when fuel went up.
LOCKED_AFTER_APPROVAL = (
    "name",
    "category",
    "legal_name",
    "registration_number",
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
            "legal_name",
            "registration_number",
            "address",
            "delivers",
            "delivery_fee",
            "is_active",
        )

    def validate(self, attrs):
        shop = self.instance
        if not shop or shop.status != BusinessStatus.APPROVED:
            return attrs

        # Only complain about a field that is actually being changed. Apps send
        # whole forms back, so the same name arriving unchanged is not an edit.
        changed = [
            field
            for field in LOCKED_AFTER_APPROVAL
            if field in attrs and attrs[field] != getattr(shop, field)
        ]
        if changed:
            raise serializers.ValidationError(
                {
                    field: (
                        "This cannot be changed now that your shop is approved. "
                        "Get in touch if it is wrong."
                    )
                    for field in changed
                }
            )
        return attrs

    def update(self, instance, validated_data):
        return update_business(
            business=instance,
            **validated_data,
        )