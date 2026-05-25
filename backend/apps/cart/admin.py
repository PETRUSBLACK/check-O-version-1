from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("line_total",)

    def line_total(self, obj):
        return obj.line_total
    line_total.short_description = "Line Total"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "item_count", "total", "created_at", "updated_at")
    readonly_fields = ("id", "total", "item_count", "created_at", "updated_at")
    inlines = [CartItemInline]

    def item_count(self, obj):
        return obj.item_count
    item_count.short_description = "Items"

    def total(self, obj):
        return obj.total
    total.short_description = "Total"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity", "created_at")
    readonly_fields = ("id", "created_at", "updated_at")
