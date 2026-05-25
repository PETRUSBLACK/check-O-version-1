from django.contrib import admin

from .models import SubscriptionPlan, VendorSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "price_monthly")


@admin.register(VendorSubscription)
class VendorSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("business", "plan", "active", "renews_at")
