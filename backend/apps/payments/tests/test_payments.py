import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessStatus
from apps.cart.services.cart_service import add_to_cart, checkout
from apps.orders.models import OrderStatus
from apps.orders.services.order_service import transition_order_status
from apps.payments.models import Payment, PaymentStatus
from apps.payments.services.gateway import confirm_payment_success, confirm_payment_via_webhook
from apps.products.models import Product
from apps.users.models import User, UserRole


def make_user(email, role=UserRole.CUSTOMER, password="testpass12345"):
    return User.objects.create_user(email=email, password=password, role=role)


def make_vendor(email="vendor@example.com"):
    return make_user(email, role=UserRole.VENDOR)


def make_business(owner):
    return Business.objects.create(
        owner=owner, name="Shop", slug="shop",
        legal_name="Shop Ltd", registration_number="RC1234567",
        status=BusinessStatus.APPROVED,
    )


def make_product(business, price="50.00", stock=20):
    return Product.objects.create(
        business=business, name="Widget", price=price, stock=stock, is_active=True,
    )


def make_paid_order(customer, product):
    add_to_cart(customer=customer, product_id=product.pk, quantity=1)
    order = checkout(customer=customer)
    return order


class PaymentInitiateTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)

    @patch("apps.payments.services.paystack.requests.post")
    def test_initiate_paystack_payment(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "status": True,
                "data": {
                    "reference": "SM-test-ref",
                    "authorization_url": "https://checkout.paystack.com/test",
                },
            },
        )
        order = make_paid_order(self.customer, self.product)
        # Reset to pending_payment for test
        order.status = OrderStatus.PENDING_PAYMENT
        order.save()

        self.client.force_authenticate(self.customer)
        res = self.client.post("/api/payments/initiate/", {
            "order_id": str(order.pk),
            "provider": "paystack",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("payment_url", res.data)
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)

    def test_initiate_with_invalid_provider_returns_400(self):
        order = make_paid_order(self.customer, self.product)
        order.status = OrderStatus.PENDING_PAYMENT
        order.save()

        self.client.force_authenticate(self.customer)
        res = self.client.post("/api/payments/initiate/", {
            "order_id": str(order.pk),
            "provider": "bitcoin",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vendor_cannot_initiate_payment(self):
        order = make_paid_order(self.customer, self.product)
        self.client.force_authenticate(self.vendor)
        res = self.client.post("/api/payments/initiate/", {
            "order_id": str(order.pk),
            "provider": "paystack",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class PaymentConfirmTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)

    def make_pending_payment(self, provider="paystack", ref="test-ref-001"):
        order = make_paid_order(self.customer, self.product)
        order.status = OrderStatus.PENDING_PAYMENT
        order.save()
        return Payment.objects.create(
            order=order,
            provider=provider,
            external_ref=ref,
            amount=order.total,
            status=PaymentStatus.PENDING,
        )

    @patch("apps.payments.services.paystack.requests.get")
    def test_confirm_via_webhook_marks_payment_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": {"status": "success", "amount": 5000, "reference": "test-ref-001"}
            },
        )
        payment = self.make_pending_payment()
        confirmed = confirm_payment_via_webhook(provider="paystack", external_ref="test-ref-001")
        self.assertEqual(confirmed.status, PaymentStatus.SUCCESS)
        confirmed.order.refresh_from_db()
        self.assertEqual(confirmed.order.status, OrderStatus.PAID)

    def test_admin_mock_confirm(self):
        payment = self.make_pending_payment()
        confirmed = confirm_payment_success(payment_id=payment.pk)
        self.assertEqual(confirmed.status, PaymentStatus.SUCCESS)


class PaystackWebhookTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)

    def _make_payment(self, ref="ps-ref-001"):
        order = make_paid_order(self.customer, self.product)
        order.status = OrderStatus.PENDING_PAYMENT
        order.save()
        return Payment.objects.create(
            order=order, provider="paystack",
            external_ref=ref, amount=order.total, status=PaymentStatus.PENDING,
        )

    def _sign(self, payload: bytes, secret: str = "test-secret") -> str:
        return hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()

    @patch("apps.payments.services.paystack.requests.get")
    def test_valid_paystack_webhook_confirms_payment(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"status": "success", "amount": 5000, "reference": "ps-ref-001"}},
        )
        payment = self._make_payment()
        payload = json.dumps({"event": "charge.success", "data": {"reference": "ps-ref-001"}}).encode()

        with self.settings(PAYSTACK_SECRET_KEY="test-secret"):
            sig = self._sign(payload)
            res = self.client.post(
                "/api/payments/webhooks/paystack/",
                data=payload, content_type="application/json",
                HTTP_X_PAYSTACK_SIGNATURE=sig,
            )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_invalid_signature_rejected(self):
        payload = json.dumps({"event": "charge.success", "data": {"reference": "ps-ref-001"}}).encode()
        res = self.client.post(
            "/api/payments/webhooks/paystack/",
            data=payload, content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE="wrong-signature",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class FlutterwaveWebhookTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)

    @patch("apps.payments.services.flutterwave.requests.get")
    def test_valid_flutterwave_webhook_confirms_payment(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [{"status": "successful", "amount": 50, "tx_ref": "fw-ref-001"}]},
        )
        order = make_paid_order(self.customer, self.product)
        order.status = OrderStatus.PENDING_PAYMENT
        order.save()
        Payment.objects.create(
            order=order, provider="flutterwave",
            external_ref="fw-ref-001", amount=order.total, status=PaymentStatus.PENDING,
        )

        payload = json.dumps({
            "event": "charge.completed",
            "data": {"status": "successful", "tx_ref": "fw-ref-001"},
        }).encode()

        with self.settings(FLUTTERWAVE_WEBHOOK_SECRET="fw-secret"):
            res = self.client.post(
                "/api/payments/webhooks/flutterwave/",
                data=payload, content_type="application/json",
                HTTP_VERIF_HASH="fw-secret",
            )

        self.assertEqual(res.status_code, status.HTTP_200_OK)


class StripeWebhookTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def _stripe_sig(self, payload: bytes, secret: str = "stripe-secret") -> str:
        ts = str(int(time.time()))
        signed = f"{ts}.{payload.decode()}"
        sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_invalid_stripe_signature_rejected(self):
        payload = json.dumps({"type": "checkout.session.completed", "data": {"object": {"id": "cs_test"}}}).encode()
        with self.settings(STRIPE_WEBHOOK_SECRET="stripe-secret"):
            res = self.client.post(
                "/api/payments/webhooks/stripe/",
                data=payload, content_type="application/json",
                HTTP_STRIPE_SIGNATURE="t=0,v1=invalid",
            )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
