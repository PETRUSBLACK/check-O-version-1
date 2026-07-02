from django.contrib import admin

from .models import (
    Business,
    Branch,
    BusinessMember,
    BusinessHours,
    BusinessRating,
    BusinessGallery,
    RestaurantProfile,
    DeliveryZone,
    BusinessVerification,
    BusinessDocument,
)


# =========================================================
# Business
# =========================================================

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "owner",
        "status",
        "is_active",
        "created_at",
    )

    list_filter = (
        "category",
        "status",
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
        "business_email",
        "business_phone",
        "owner__email",
    )

    autocomplete_fields = (
        "owner",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    date_hierarchy = "created_at"

    ordering = (
        "-created_at",
    )

    list_select_related = (
        "owner",
    )


# =========================================================
# Branch
# =========================================================

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "business",
        "city",
        "state",
        "phone_number",
        "is_active",
    )

    list_filter = (
        "city",
        "state",
        "country",
        "is_active",
    )

    search_fields = (
        "name",
        "business__name",
        "city",
        "state",
    )

    autocomplete_fields = (
        "business",
    )

    list_select_related = (
        "business",
    )


# =========================================================
# Business Members
# =========================================================

@admin.register(BusinessMember)
class BusinessMemberAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business",
        "branch",
        "role",
        "is_active",
        "joined_at",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "user__email",
        "business__name",
    )

    autocomplete_fields = (
        "user",
        "business",
        "branch",
        "invited_by",
    )

    list_select_related = (
        "user",
        "business",
        "branch",
    )


# =========================================================
# Business Hours
# =========================================================

@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = (
        "branch",
        "weekday",
        "opening_time",
        "closing_time",
        "is_closed",
        "is_twenty_four_hours",
    )

    list_filter = (
        "weekday",
        "is_closed",
        "is_twenty_four_hours",
    )

    autocomplete_fields = (
        "branch",
    )

    list_select_related = (
        "branch",
    )


# =========================================================
# Gallery
# =========================================================

@admin.register(BusinessGallery)
class BusinessGalleryAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "caption",
        "display_order",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "business__name",
        "caption",
    )

    autocomplete_fields = (
        "business",
    )

    list_select_related = (
        "business",
    )

    ordering = (
        "display_order",
        "-created_at",
    )

# =========================================================
# Rating
# =========================================================

@admin.register(BusinessRating)
class BusinessRatingAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "customer",
        "score",
        "is_visible",
        "created_at",
    )

    list_filter = (
        "score",
        "is_visible",
    )

    search_fields = (
        "business__name",
        "customer__email",
        "review",
    )

    autocomplete_fields = (
        "business",
        "customer",
    )

    list_select_related = (
        "business",
        "customer",
    )

    ordering = (
        "-created_at",
    )

# =========================================================
# Restaurant
# =========================================================

@admin.register(RestaurantProfile)
class RestaurantProfileAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "cuisine",
        "accepts_delivery",
        "accepts_takeaway",
        "accepts_reservations",
    )

    search_fields = (
        "business__name",
        "cuisine",
    )

    autocomplete_fields = (
        "business",
    )


# =========================================================
# Delivery Zone
# =========================================================

@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = (
        "branch",
        "name",
        "radius_km",
        "delivery_fee",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "branch__name",
        "name",
    )

    autocomplete_fields = (
        "branch",
    )

    list_select_related = (
        "branch",
    )


# =========================================================
# Verification
# =========================================================

@admin.register(BusinessVerification)
class BusinessVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "status",
        "verified_by",
        "submitted_at",
        "verified_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "business__name",
        "registration_number",
        "legal_name",
    )

    autocomplete_fields = (
        "business",
        "verified_by",
    )

    list_select_related = (
        "business",
        "verified_by",
    )


# =========================================================
# Documents
# =========================================================

@admin.register(BusinessDocument)
class BusinessDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "document_type",
        "title",
        "uploaded_by",
        "is_verified",
        "expiry_date",
        "created_at",
    )

    list_filter = (
        "document_type",
        "is_verified",
    )

    search_fields = (
        "business__name",
        "title",
        "description",
    )

    autocomplete_fields = (
        "business",
        "uploaded_by",
        "verified_by",
    )

    list_select_related = (
        "business",
        "uploaded_by",
        "verified_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "verified_at",
    )

    ordering = (
        "-created_at",
    )