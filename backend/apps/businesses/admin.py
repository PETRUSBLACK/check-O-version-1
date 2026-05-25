from django.contrib import admin

from .models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "owner",
        "status",
        "legal_name",
        "registration_number",
        "submitted_for_review_at",
        "verified_at",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = (
        "name",
        "slug",
        "legal_name",
        "registration_number",
        "owner__email",
    )
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("submitted_for_review_at", "verified_at", "created_at", "updated_at")
