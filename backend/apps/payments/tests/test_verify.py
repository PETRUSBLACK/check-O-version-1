"""
Checking a payment when the customer comes back from the gateway.

The gateway has the final word. These tests pin down what happens when it says
yes, when it says no, when it says yes for too little, and when someone asks
about a payment that isn't theirs.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.cart.services.cart_service import add_to_cart, checkout_cart
from apps.orders.models import OrderStatus
from apps.payments.models import Payment, PaymentStatus
from apps.payments.services.base_gateway import VerifyResult
from apps.products.models import Product
from apps.users.models import User, UserRole


class VerifyPaymentTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        owner = User.objects.create_user(
            email="shopowner@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.shop = Business.objects.create(
            owner=owner,
            name="Corner Shop",
            slug="corner-shop",
            legal_name="Corner Shop Ltd",
            registration_number="RC1111111",
            status=BusinessStatus.APPROVED,
        )
        self.product = Product.objects.create(
            business=self.shop, name="Rice", price=Decimal("10000.00"), stock=10, is_active=True
        )
        self.customer = User.objects.create_user(
            email="payer@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        add_to_cart(customer=self.customer, product_id=self.product.id, quantity=2)
        self.group = checkout_cart(customer=self.customer)
        self.payment = Payment.objects.create(
            checkout_group=self.group,
            provider="paystack",
            amount=Decimal("20000.00"),
            external_ref="SM-TEST-abc123",
            status=PaymentStatus.PENDING,
        )
        self.url = f"/api/payments/{self.payment.id}/verify/"
        self.client.force_authenticate(self.customer)

    def gateway_says(self, *, success: bool, amount="20000.00"):
        return patch(
            "apps.payments.services.gateway.get_gateway",
            return_value=_FakeGateway(success=success, amount=Decimal(amount)),
        )

    # ─── The gateway said yes ─────────────────────────────────────────────────

    def test_payment_confirmed_marks_the_orders_paid(self):
        with self.gateway_says(success=True):
            res = self.client.post(self.url)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["payment"]["status"], PaymentStatus.SUCCESS)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.SUCCESS)
        order = self.group.orders.get()
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PAID)
        self.assertIsNotNone(order.paid_at)

    def test_checking_twice_is_harmless(self):
        with self.gateway_says(success=True):
            self.client.post(self.url)
            res = self.client.post(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["payment"]["status"], PaymentStatus.SUCCESS)
        self.assertEqual(self.group.orders.count(), 1)

    def test_the_response_carries_the_checkout_back(self):
        with self.gateway_says(success=True):
            res = self.client.post(self.url)
        self.assertIn("checkout", res.data)
        self.assertEqual(res.data["checkout"]["id"], str(self.group.id))

    # ─── The gateway said no ──────────────────────────────────────────────────

    def test_unsuccessful_payment_is_explained_and_orders_stay_unpaid(self):
        with self.gateway_says(success=False):
            res = self.client.post(self.url)
        self.assertEqual(res.status_code, 400)
        self.assertIn("didn't go through", res.data["detail"])

        order = self.group.orders.get()
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PENDING_PAYMENT)

    def test_paying_less_than_the_total_is_refused(self):
        """The amount is set by us at initiation; anything short is wrong."""
        with self.gateway_says(success=True, amount="500.00"):
            res = self.client.post(self.url)
        self.assertEqual(res.status_code, 400)
        self.assertIn("less than the total", res.data["detail"])

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.FAILED)
        order = self.group.orders.get()
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PENDING_PAYMENT)

    def test_paying_more_than_the_total_still_counts(self):
        with self.gateway_says(success=True, amount="25000.00"):
            res = self.client.post(self.url)
        self.assertEqual(res.status_code, 200, res.data)

    # ─── Whose payment is it ──────────────────────────────────────────────────

    def test_someone_elses_payment_is_refused(self):
        stranger = User.objects.create_user(
            email="stranger@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.client.force_authenticate(stranger)
        with self.gateway_says(success=True):
            res = self.client.post(self.url)
        self.assertEqual(res.status_code, 403)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PENDING)

    def test_signed_out_is_refused(self):
        self.client.force_authenticate(None)
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, 401)

    def test_unknown_payment_is_a_404(self):
        res = self.client.post("/api/payments/11111111-1111-1111-1111-111111111111/verify/")
        self.assertEqual(res.status_code, 404)


class _FakeGateway:
    """Stands in for Paystack so the tests never touch the network."""

    def __init__(self, *, success: bool, amount: Decimal):
        self.success = success
        self.amount = amount

    def verify(self, *, external_ref: str) -> VerifyResult:
        return VerifyResult(
            success=self.success,
            external_ref=external_ref,
            amount=self.amount,
            provider_payload={},
        )
