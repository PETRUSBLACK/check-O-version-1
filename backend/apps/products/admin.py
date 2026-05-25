from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "price", "stock", "is_active", "created_at")
    list_filter = ("is_active", "business", "created_at")
    search_fields = ("name", "business__name")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
