from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "provider", "status", "amount", "created_at")
    list_filter = ("provider", "status", "created_at")
    search_fields = ("id", "order__id", "order__customer__email", "external_ref")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "created_at"
