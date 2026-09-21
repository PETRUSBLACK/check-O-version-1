"""
Tests for:
- 30-minute stock holds on unpaid orders (and automatic release)
- stock always returning to the bucket it came from (allocation vs main stock)
- cancel rules for customers, vendors and admins
- refund flagging + "Refunds to process" admin
- background tasks (expire unpaid orders, 2-hour vendor reminder, run_tasks command)
"""

from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.cart.services.cart_service import add_to_cart, checkout
from apps.notifications.models import Notification
from apps.orders.models import (
    CancellationReason,
    CancelledBy,
    FulfilmentType,
    Order,
    OrderStatus,
    RefundQueue,
    RefundStatus,
    StockReservation,
    StockSource,
)
from apps.orders.services.order_service import (
    OrderFlowError,
    OrderPermissionError,
    cancel_order,
    expire_pickup_order,
    mark_order_paid,
    transition_order_status,
)
from apps.orders.services.stock_service import PAYMENT_WINDOW_MINUTES
from apps.payments.models import Payment, PaymentStatus
from apps.payments.services.gateway import confirm_payment_success, initiate_payment
from apps.products.models import Product
from apps.users.models import User, UserRole
import tasks


def make_user(email, role=UserRole.CUSTOMER):
    return User.objects.create_user(email=email, password="testpass12345", role=role)


def make_shop(owner, slug="shop"):
    return Business.objects.create(
        owner=owner, name=f"Shop {slug}", slug=slug,
        legal_name="Shop Ltd", registration_number=f"RC-{slug}",
        status=BusinessStatus.APPROVED,
    )


def make_product(business, stock=20, allocation=None, name="Garri 5kg"):
    return Product.objects.create(
        business=business, name=name, price=Decimal("4500.00"),
        stock=stock, smartmall_allocation=allocation, is_active=True,
    )


def place_order(customer, product, quantity=1):
    add_to_cart(customer=customer, product_id=product.pk, quantity=quantity)
    return checkout(customer=customer)


def pay(order):
    payment = Payment.objects.create(
        order=order, provider="paystack", external_ref=f"ref-{order.pk}",
        amount=order.total, status=PaymentStatus.PENDING,
    )
    confirm_payment_success(payment_id=payment.pk)
    order.refresh_from_db()
    return order


def expire_holds(order):
    StockReservation.objects.filter(order=order).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )


class Base(TestCase):
    def setUp(self):
        self.vendor = make_user("vendor@example.com", UserRole.VENDOR)
        self.shop = make_shop(self.vendor)
        self.customer = make_user("ada@example.com")
        # Shop has 30 on the shelf, 5 set aside in the Check-O basket
        self.allocated = make_product(self.shop, stock=30, allocation=5, name="Allocated")
        self.plain = make_product(self.shop, stock=10, allocation=None, name="Plain")

    def reload(self, *objs):
        for o in objs:
            o.refresh_from_db()


# ─── Stock holds ──────────────────────────────────────────────────────────────

class StockHoldTest(Base):

    def test_checkout_holds_stock_from_the_right_bucket(self):
        order = place_order(self.customer, self.allocated, 2)
        self.reload(self.allocated)
        self.assertEqual(self.allocated.smartmall_allocation, 3)
        self.assertEqual(self.allocated.stock, 30)  # shop shelf untouched

        res = StockReservation.objects.get(order=order)
        self.assertEqual(res.source, StockSource.ALLOCATION)
        self.assertEqual(res.quantity, 2)
        window = res.expires_at - res.created_at
        self.assertAlmostEqual(window.total_seconds(), PAYMENT_WINDOW_MINUTES * 60, delta=5)

    def test_plain_product_holds_main_stock(self):
        order = place_order(self.customer, self.plain, 3)
        self.reload(self.plain)
        self.assertEqual(self.plain.stock, 7)
        self.assertEqual(StockReservation.objects.get(order=order).source, StockSource.STOCK)

    def test_unpaid_order_expires_and_returns_stock_to_allocation(self):
        order = place_order(self.customer, self.allocated, 2)
        expire_holds(order)

        cancelled = tasks.expire_unpaid_orders()

        self.assertEqual(cancelled, 1)
        self.reload(order, self.allocated)
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.cancelled_by, CancelledBy.SYSTEM)
        self.assertEqual(order.cancellation_reason, CancellationReason.PAYMENT_TIMEOUT)
        self.assertEqual(order.refund_status, RefundStatus.NONE)
        self.assertEqual(self.allocated.smartmall_allocation, 5)  # back in the basket
        self.assertEqual(self.allocated.stock, 30)                # shelf not inflated

    def test_orders_within_the_window_are_not_expired(self):
        order = place_order(self.customer, self.plain, 1)
        self.assertEqual(tasks.expire_unpaid_orders(), 0)
        self.reload(order)
        self.assertEqual(order.status, OrderStatus.PENDING_PAYMENT)

    def test_expired_hold_is_released_when_someone_else_adds_to_cart(self):
        # Ada takes the whole basket and never pays
        order = place_order(self.customer, self.allocated, 5)
        expire_holds(order)
        # No background job has run — Bola can still buy
        bola = make_user("bola@example.com")
        add_to_cart(customer=bola, product_id=self.allocated.pk, quantity=5)
        self.reload(order)
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_paid_order_is_confirmed_and_never_expired(self):
        order = pay(place_order(self.customer, self.allocated, 2))
        self.assertEqual(order.status, OrderStatus.PAID)
        self.assertIsNotNone(order.paid_at)
        self.assertTrue(StockReservation.objects.get(order=order).confirmed)

        expire_holds(order)
        self.assertEqual(tasks.expire_unpaid_orders(), 0)
        self.reload(order, self.allocated)
        self.assertEqual(order.status, OrderStatus.PAID)
        self.assertEqual(self.allocated.smartmall_allocation, 3)

    def test_payment_after_expiry_is_flagged_for_refund(self):
        order = place_order(self.customer, self.plain, 1)
        expire_holds(order)
        tasks.expire_unpaid_orders()
        Payment.objects.create(
            order=order, provider="paystack", external_ref="late",
            amount=order.total, status=PaymentStatus.SUCCESS,
        )
        mark_order_paid(order_id=order.pk)
        self.reload(order)
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.refund_status, RefundStatus.DUE)
        self.assertTrue(Notification.objects.filter(user=self.customer, title__icontains="refund").exists()
                        or Notification.objects.filter(user=self.customer, body__icontains="refund").exists())

    @patch("apps.payments.services.gateway.get_gateway")
    def test_cannot_start_payment_for_cancelled_order(self, _gw):
        order = place_order(self.customer, self.plain, 1)
        cancel_order(order_id=order.pk, user=self.customer)
        with self.assertRaises(ValueError):
            initiate_payment(order_id=order.pk, provider="paystack", amount=order.total)


# ─── Cancel rules ─────────────────────────────────────────────────────────────

class CancelRulesTest(Base):

    def test_customer_cancels_unpaid_order(self):
        order = place_order(self.customer, self.allocated, 2)
        cancel_order(order_id=order.pk, user=self.customer)
        self.reload(order, self.allocated)
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.cancelled_by, CancelledBy.CUSTOMER)
        self.assertEqual(order.cancellation_reason, CancellationReason.CUSTOMER_REQUEST)
        self.assertEqual(order.refund_status, RefundStatus.NONE)
        self.assertEqual(self.allocated.smartmall_allocation, 5)

    def test_customer_cancels_paid_order_before_shop_starts(self):
        order = pay(place_order(self.customer, self.plain, 1))
        cancel_order(order_id=order.pk, user=self.customer)
        self.reload(order, self.plain)
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.refund_status, RefundStatus.DUE)
        self.assertEqual(self.plain.stock, 10)

    def test_customer_cannot_cancel_once_shop_starts(self):
        order = pay(place_order(self.customer, self.plain, 1))
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PROCESSING)
        with self.assertRaises(OrderFlowError):
            cancel_order(order_id=order.pk, user=self.customer)

    def test_vendor_must_give_reason(self):
        order = pay(place_order(self.customer, self.plain, 1))
        with self.assertRaises(OrderFlowError):
            cancel_order(order_id=order.pk, user=self.vendor)
        with self.assertRaises(OrderFlowError):
            cancel_order(order_id=order.pk, user=self.vendor, reason="other", note="  ")

    def test_vendor_cancels_while_packaging_with_reason(self):
        order = pay(place_order(self.customer, self.allocated, 1))
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PROCESSING)
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PACKAGING)
        cancel_order(order_id=order.pk, user=self.vendor, reason="item_damaged")
        self.reload(order, self.allocated)
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.cancelled_by, CancelledBy.VENDOR)
        self.assertEqual(order.cancelled_by_user, self.vendor)
        self.assertEqual(order.cancellation_reason, CancellationReason.ITEM_DAMAGED)
        self.assertEqual(order.refund_status, RefundStatus.DUE)
        self.assertEqual(self.allocated.smartmall_allocation, 5)

    def test_nobody_can_cancel_after_shipping(self):
        order = pay(place_order(self.customer, self.plain, 1))
        for s in (OrderStatus.PROCESSING, OrderStatus.PACKAGING, OrderStatus.SHIPPED):
            transition_order_status(order_id=order.pk, to_status=s)
        with self.assertRaises(OrderFlowError):
            cancel_order(order_id=order.pk, user=self.vendor, reason="out_of_stock")
        with self.assertRaises(OrderFlowError):
            cancel_order(order_id=order.pk, user=self.customer)

    def test_other_vendor_cannot_cancel(self):
        order = place_order(self.customer, self.plain, 1)
        stranger = make_user("other@example.com", UserRole.VENDOR)
        with self.assertRaises(OrderPermissionError):
            cancel_order(order_id=order.pk, user=stranger, reason="out_of_stock")

    def test_cannot_cancel_twice_or_release_stock_twice(self):
        order = place_order(self.customer, self.plain, 2)
        cancel_order(order_id=order.pk, user=self.customer)
        with self.assertRaises(OrderFlowError):
            cancel_order(order_id=order.pk, user=self.customer)
        self.reload(self.plain)
        self.assertEqual(self.plain.stock, 10)


class CancelAPITest(Base):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_customer_cancel_endpoint(self):
        order = place_order(self.customer, self.plain, 1)
        self.client.force_authenticate(self.customer)
        res = self.client.post(f"/api/orders/{order.pk}/cancel/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "cancelled")
        self.assertEqual(res.data["cancelled_by"], "customer")
        self.assertEqual(res.data["refund_status"], "none")

    def test_vendor_cancel_endpoint_requires_reason(self):
        order = pay(place_order(self.customer, self.plain, 1))
        self.client.force_authenticate(self.vendor)
        res = self.client.post(f"/api/orders/{order.pk}/cancel/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.post(
            f"/api/orders/{order.pk}/cancel/", {"reason": "out_of_stock"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["refund_status"], "due")

    def test_stranger_gets_403(self):
        order = place_order(self.customer, self.plain, 1)
        self.client.force_authenticate(make_user("x@example.com"))
        res = self.client.post(f"/api/orders/{order.pk}/cancel/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_transition_endpoint_follows_cancel_rules(self):
        order = pay(place_order(self.customer, self.plain, 1))
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PROCESSING)
        self.client.force_authenticate(self.customer)
        res = self.client.post(
            f"/api/orders/{order.pk}/transition/", {"status": "cancelled"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ─── Pickup expiry ────────────────────────────────────────────────────────────

class PickupExpiryTest(Base):

    def test_expired_pickup_returns_stock_to_allocation_and_flags_refund(self):
        order = place_order(self.customer, self.allocated, 2)
        Order.objects.filter(pk=order.pk).update(fulfilment_type=FulfilmentType.PICKUP)
        order = pay(order)
        transition_order_status(order_id=order.pk, to_status=OrderStatus.READY_FOR_PICKUP)

        expire_pickup_order(order_id=order.pk)

        self.reload(order, self.allocated)
        self.assertEqual(order.status, OrderStatus.EXPIRED)
        self.assertEqual(order.refund_status, RefundStatus.DUE)
        self.assertEqual(self.allocated.smartmall_allocation, 5)
        self.assertEqual(self.allocated.stock, 30)  # shelf count not inflated


# ─── Vendor reminder + run_tasks ──────────────────────────────────────────────

class BackgroundTaskTest(Base):

    def test_vendor_reminded_once_after_two_hours(self):
        order = pay(place_order(self.customer, self.plain, 1))
        Order.objects.filter(pk=order.pk).update(paid_at=timezone.now() - timedelta(hours=3))

        self.assertEqual(tasks.remind_vendors_waiting(), 1)
        self.assertTrue(Notification.objects.filter(user=self.vendor, title__icontains="waiting").exists())
        # Second run: no duplicate reminder, and the order is NOT cancelled
        self.assertEqual(tasks.remind_vendors_waiting(), 0)
        self.reload(order)
        self.assertEqual(order.status, OrderStatus.PAID)

    def test_no_reminder_before_two_hours(self):
        pay(place_order(self.customer, self.plain, 1))
        self.assertEqual(tasks.remind_vendors_waiting(), 0)

    def test_run_tasks_command(self):
        order = place_order(self.customer, self.plain, 1)
        expire_holds(order)
        out = StringIO()
        call_command("run_tasks", "--all", stdout=out)
        self.assertIn("Tasks complete", out.getvalue())
        self.reload(order)
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_run_tasks_scheduled_mode(self):
        out = StringIO()
        call_command("run_tasks", "--scheduled", stdout=out)
        self.assertIn("Running frequent tasks", out.getvalue())


# ─── Admin ────────────────────────────────────────────────────────────────────

class RefundAdminTest(Base):

    def setUp(self):
        super().setUp()
        self.admin_user = User.objects.create_superuser(email="admin@example.com", password="adminpass123")
        self.client.force_login(self.admin_user)

    def test_refund_queue_lists_only_refund_due_and_can_mark_refunded(self):
        due = pay(place_order(self.customer, self.plain, 1))
        cancel_order(order_id=due.pk, user=self.customer)
        not_due = place_order(make_user("b@example.com"), self.plain, 1)

        self.assertEqual(list(RefundQueue.objects.filter(refund_status=RefundStatus.DUE).values_list("pk", flat=True)), [due.pk])

        res = self.client.get("/admin/orders/refundqueue/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, str(due.pk))
        self.assertNotContains(res, str(not_due.pk))

        res = self.client.post("/admin/orders/refundqueue/", {
            "action": "mark_refunded",
            "_selected_action": [str(due.pk)],
        })
        self.assertEqual(res.status_code, 302)
        due.refresh_from_db()
        self.assertEqual(due.refund_status, RefundStatus.REFUNDED)
        self.assertIsNotNone(due.refunded_at)

    def test_business_admin_shows_vendor_cancellations(self):
        order = pay(place_order(self.customer, self.plain, 1))
        cancel_order(order_id=order.pk, user=self.vendor, reason="out_of_stock")
        res = self.client.get("/admin/businesses/business/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Vendor cancellations")
