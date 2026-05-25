from django.contrib import admin

from .models import Shipment


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "mode", "partner", "status", "tracking_number")
    list_filter = ("mode", "partner", "status", "created_at")
    search_fields = ("id", "order__id", "order__customer__email", "tracking_number")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "created_at"
