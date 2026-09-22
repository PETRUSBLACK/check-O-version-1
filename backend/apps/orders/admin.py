from django.contrib import admin, messages
from django.utils import timezone

from .models import CheckoutGroup, Order, OrderItem, RefundQueue, RefundStatus


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "business", "status", "total", "refund_status", "created_at")
    list_filter = ("status", "refund_status", "cancelled_by", "cancellation_reason", "created_at")
    raw_id_fields = ("checkout_group",)
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
        "id", "customer", "business", "refund_amount", "status", "cancellation_reason",
        "cancelled_by", "payment_reference", "cancelled_at",
    )
    list_filter = ("cancellation_reason", "cancelled_by")
    search_fields = (
        "id", "customer__email", "payments__external_ref",
        "checkout_group__payments__external_ref",
    )
    actions = ["mark_refunded"]
    ordering = ("cancelled_at",)

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .filter(refund_status=RefundStatus.DUE)
            .select_related("customer", "business", "checkout_group")
            .prefetch_related("payments", "checkout_group__payments")
        )

    @admin.display(description="Refund amount (₦)")
    def refund_amount(self, obj):
        # If the customer paid for several shops at once, refund only this
        # shop's part (a partial refund in Paystack).
        return obj.total

    @admin.display(description="Paystack reference")
    def payment_reference(self, obj):
        payments = list(obj.payments.all())
        if obj.checkout_group_id:
            payments += list(obj.checkout_group.payments.all())
        refs = [p.external_ref for p in payments if p.status == "success"]
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


class CheckoutGroupOrderInline(admin.TabularInline):
    model = Order
    fk_name = "checkout_group"
    fields = ("id", "business", "status", "total", "refund_status")
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(CheckoutGroup)
class CheckoutGroupAdmin(admin.ModelAdmin):
    """One customer checkout = one payment, split into one order per shop."""
    list_display = ("id", "customer", "total", "created_at")
    search_fields = ("id", "customer__email", "payments__external_ref")
    readonly_fields = ("id", "customer", "total", "created_at", "updated_at")
    inlines = [CheckoutGroupOrderInline]
