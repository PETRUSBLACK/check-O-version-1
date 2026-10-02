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
        if Business.objects.filter(slug__iexact=value).exists():
            raise serializers.ValidationError("A business with this slug already exists.")

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
            "legal_name",
            "registration_number",
            "address",
            "delivers",
            "delivery_fee",
            "is_active",
        )

    def validate(self, attrs):
        if self.instance and self.instance.status == BusinessStatus.APPROVED:
            raise serializers.ValidationError("Approved businesses cannot be edited.")
        return attrs

    def update(self, instance, validated_data):
        return update_business(
            business=instance,
            **validated_data,
        )