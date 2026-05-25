from django.contrib import admin

from .models import ProductPromotion


@admin.register(ProductPromotion)
class ProductPromotionAdmin(admin.ModelAdmin):
    list_display = ("title", "product", "boost_weight", "starts_at", "ends_at")
