from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "read_at", "created_at")
    list_filter = ("read_at", "created_at")
    search_fields = ("id", "user__email", "title", "body")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "created_at"
