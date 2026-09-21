from django.contrib import admin, messages
from django.utils import timezone

from .models import Order, OrderItem, RefundQueue, RefundStatus


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total", "refund_status", "created_at")
    list_filter = ("status", "refund_status", "cancelled_by", "cancellation_reason", "created_at")
    search_fields = ("id", "customer__email")
    readonly_fields = (
        "id", "created_at", "updated_at", "paid_at", "vendor_reminder_sent_at",
        "cancelled_at", "cancelled_by", "cancelled_by_user", "cancellation_reason",
        "cancellation_note", "refunded_at",
    )
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]


@admin.register(RefundQueue)
class RefundQueueAdmin(admin.ModelAdmin):
    """
    Paid orders that were cancelled or expired and need a refund.
    Process each refund in the Paystack dashboard using the payment reference,
    then select it here and run "Mark as refunded".
    """
    list_display = (
        "id", "customer", "total", "status", "cancellation_reason",
        "cancelled_by", "payment_reference", "cancelled_at",
    )
    list_filter = ("cancellation_reason", "cancelled_by")
    search_fields = ("id", "customer__email", "payments__external_ref")
    actions = ["mark_refunded"]
    ordering = ("cancelled_at",)

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .filter(refund_status=RefundStatus.DUE)
            .select_related("customer")
            .prefetch_related("payments")
        )

    @admin.display(description="Paystack reference")
    def payment_reference(self, obj):
        refs = [p.external_ref for p in obj.payments.all() if p.status == "success"]
        return ", ".join(refs) or "—"

    @admin.action(description="Mark as refunded (after refunding in Paystack)")
    def mark_refunded(self, request, queryset):
        count = queryset.filter(refund_status=RefundStatus.DUE).update(
            refund_status=RefundStatus.REFUNDED,
            refunded_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.message_user(request, f"{count} order(s) marked as refunded.", messages.SUCCESS)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
