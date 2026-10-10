"""
A customer who has paid must not depend on the phone coming back.

Found 2026-10-10. Petrus paid NGN 1,000 on Paystack's test page; Paystack's
dashboard said Success, Check-O's admin said Pending, and his order said "waiting
for payment". Nothing ever asked Paystack. The app asks only when the customer is
sent back from the payment page — which never happens in Expo Go, or when the
page is closed by hand — and Paystack's webhook helps only once somebody has
configured it in the dashboard.

So a task that runs every five minutes asks about anything still waiting.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

import tasks
from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.cart.services.cart_service import add_to_cart, checkout_cart
from apps.notifications.models import Notification
from apps.orders.models import OrderStatus, StockReservation
from apps.payments.models import Payment, PaymentStatus
from apps.payments.services.base_gateway import VerifyResult
from apps.products.models import Product
from apps.users.models import User, UserRole


class _Gateway:
    def __init__(self, *, success, declined=None, amount="20000.00"):
        self.success, self.declined, self.amount = success, declined, Decimal(amount)

    def verify(self, *, external_ref):
        return VerifyResult(
            success=self.success,
            external_ref=external_ref,
            amount=self.amount,
            provider_payload={},
            declined=self.declined,
        )


class SettlePendingPaymentsTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="shopowner@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        shop = Business.objects.create(
            owner=self.owner,
            name="Corner Shop",
            slug="corner-shop",
            legal_name="Corner Shop Ltd",
            registration_number="RC1111111",
            status=BusinessStatus.APPROVED,
        )
        product = Product.objects.create(
            business=shop, name="Rice", price=Decimal("10000.00"), stock=10, is_active=True
        )
        customer = User.objects.create_user(
            email="payer@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        add_to_cart(customer=customer, product_id=product.id, quantity=2)
        self.group = checkout_cart(customer=customer)
        self.payment = Payment.objects.create(
            checkout_group=self.group,
            provider="paystack",
            amount=Decimal("20000.00"),
            external_ref="SM-TEST-abc123",
            status=PaymentStatus.PENDING,
        )
        self.age_payment(minutes=5)

    def age_payment(self, *, minutes):
        Payment.objects.filter(pk=self.payment.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes)
        )

    def paystack_says(self, **kwargs):
        return patch(
            "apps.payments.services.gateway.get_gateway", return_value=_Gateway(**kwargs)
        )

    def order(self):
        order = self.group.orders.get()
        order.refresh_from_db()
        return order

    def test_a_payment_paystack_has_taken_is_settled_without_the_phone(self):
        with self.paystack_says(success=True):
            tasks.settle_pending_payments()

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.SUCCESS)
        self.assertEqual(self.order().status, OrderStatus.PAID)

    def test_the_shop_is_told_when_it_settles(self):
        with self.paystack_says(success=True):
            tasks.settle_pending_payments()
        self.assertTrue(
            Notification.objects.filter(user=self.owner, event_type="vendor.new_order").exists()
        )

    def test_a_payment_still_in_progress_stays_pending(self):
        with self.paystack_says(success=False, declined=False):
            tasks.settle_pending_payments()
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PENDING)

    def test_and_is_settled_on_a_later_run_once_paid(self):
        with self.paystack_says(success=False, declined=False):
            tasks.settle_pending_payments()
        with self.paystack_says(success=True):
            tasks.settle_pending_payments()
        self.assertEqual(self.order().status, OrderStatus.PAID)

    def test_a_declined_payment_is_marked_failed(self):
        with self.paystack_says(success=False, declined=True):
            tasks.settle_pending_payments()
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.FAILED)

    def test_a_payment_the_app_may_still_be_checking_is_left_alone(self):
        """The customer has just left the page; give the app first go."""
        self.age_payment(minutes=0)
        with self.paystack_says(success=True):
            self.assertEqual(tasks.settle_pending_payments(), 0)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PENDING)

    def test_a_day_old_abandoned_payment_is_not_chased_forever(self):
        self.age_payment(minutes=60 * 25)
        with self.paystack_says(success=True):
            self.assertEqual(tasks.settle_pending_payments(), 0)

    def test_running_it_twice_changes_nothing_the_second_time(self):
        with self.paystack_says(success=True):
            tasks.settle_pending_payments()
            tasks.settle_pending_payments()
        self.assertEqual(self.group.orders.count(), 1)
        self.assertEqual(
            Notification.objects.filter(user=self.owner, event_type="vendor.new_order").count(), 1
        )

    def test_paid_money_beats_the_clock(self):
        """
        The ordering that matters. An order whose 30 minutes have run out must
        not be cancelled if Paystack already has the money.
        """
        StockReservation.objects.filter(order__checkout_group=self.group).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        with self.paystack_says(success=True):
            tasks.run_all_frequent_tasks()
        self.assertEqual(self.order().status, OrderStatus.PAID)
