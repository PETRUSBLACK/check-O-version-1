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


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "owner",
        "status",
        "business_email",
        "business_phone",
        "is_active",
        "created_at",
    )

    list_filter = (
        "status",
        "category",
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
        "business_email",
        "business_phone",
        "owner__email",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    readonly_fields = (
        "created_at",
        "updated_at",
    )


admin.site.register(Branch)
admin.site.register(BusinessMember)
admin.site.register(BusinessHours)
admin.site.register(BusinessRating)
admin.site.register(BusinessGallery)
admin.site.register(RestaurantProfile)
admin.site.register(DeliveryZone)
admin.site.register(BusinessVerification)
admin.site.register(BusinessDocument)