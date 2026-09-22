"""
Tests for multi-shop checkout: one cart → one order per shop → one payment.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.cart.services.cart_service import CartError, add_to_cart, checkout, checkout_cart
from apps.notifications.models import Notification
from apps.orders.models import (
    CheckoutGroup,
    Order,
    OrderStatus,
    RefundQueue,
    RefundStatus,
    StockReservation,
)
from apps.orders.services.order_service import (
    OrderFlowError,
    cancel_order,
    create_order_with_lines,
)
from apps.payments.models import Payment, PaymentStatus
from apps.payments.services.base_gateway import InitiateResult, VerifyResult
from apps.payments.services.gateway import (
    confirm_payment_success,
    confirm_payment_via_webhook,
    initiate_checkout_payment,
    initiate_payment,
)
from apps.products.models import Product
from apps.users.models import User, UserRole
import tasks


def make_user(email, role=UserRole.CUSTOMER):
    return User.objects.create_user(email=email, password="testpass12345", role=role)


def make_shop(owner, slug):
    return Business.objects.create(
        owner=owner, name=f"Shop {slug}", slug=slug,
        legal_name=f"{slug} Ltd", registration_number=f"RC-{slug}",
        status=BusinessStatus.APPROVED,
    )


def make_product(business, name, price, stock=10, allocation=None):
    return Product.objects.create(
        business=business, name=name, price=Decimal(price),
        stock=stock, smartmall_allocation=allocation, is_active=True,
    )


def fake_gateway(ref="PSK-REF-1"):
    gw = MagicMock()
    gw.initiate.return_value = InitiateResult(
        external_ref=ref, payment_url="https://pay.example/x", provider_payload={}
    )
    gw.verify.return_value = VerifyResult(
        success=True, external_ref=ref, amount=Decimal("0"), provider_payload={}
    )
    return gw


class Base(TestCase):
    def setUp(self):
        self.vendor_a = make_user("a@shop.com", UserRole.VENDOR)
        self.vendor_b = make_user("b@shop.com", UserRole.VENDOR)
        self.shop_a = make_shop(self.vendor_a, "ogbe-foods")
        self.shop_b = make_shop(self.vendor_b, "cable-point-phones")
        self.garri = make_product(self.shop_a, "Garri 5kg", "4500.00", stock=30, allocation=5)
        self.rice = make_product(self.shop_a, "Rice 5kg", "8000.00", stock=10)
        self.charger = make_product(self.shop_b, "Phone charger", "3500.00", stock=10)
        self.ada = make_user("ada@example.com")

    def fill_cart(self):
        add_to_cart(customer=self.ada, product_id=self.garri.pk, quantity=1)   # shop A
        add_to_cart(customer=self.ada, product_id=self.charger.pk, quantity=2)  # shop B
        add_to_cart(customer=self.ada, product_id=self.rice.pk, quantity=1)     # shop A

    def orders_by_shop(self, group):
        return {o.business_id: o for o in group.orders.all()}


class CheckoutSplitTest(Base):

    def test_cart_splits_into_one_order_per_shop(self):
        self.fill_cart()
        group = checkout_cart(customer=self.ada)

        self.assertEqual(group.orders.count(), 2)
        by_shop = self.orders_by_shop(group)
        a, b = by_shop[self.shop_a.pk], by_shop[self.shop_b.pk]

        self.assertEqual(a.total, Decimal("12500.00"))  # garri + rice
        self.assertEqual(b.total, Decimal("7000.00"))   # 2 chargers
        self.assertEqual(group.total, Decimal("19500.00"))
        self.assertEqual(set(a.items.values_list("product_id", flat=True)), {self.garri.pk, self.rice.pk})
        self.assertEqual(list(b.items.values_list("product_id", flat=True)), [self.charger.pk])
        for order in (a, b):
            self.assertEqual(order.status, OrderStatus.PENDING_PAYMENT)
            self.assertEqual(order.customer, self.ada)
        # Stock is held per shop order
        self.assertEqual(StockReservation.objects.filter(order=a).count(), 2)
        self.assertEqual(StockReservation.objects.filter(order=b).count(), 1)

    def test_single_shop_checkout_helper_refuses_multi_shop_cart(self):
        self.fill_cart()
        with self.assertRaises(CartError):
            checkout(customer=self.ada)

    def test_single_shop_cart_still_works_with_checkout(self):
        add_to_cart(customer=self.ada, product_id=self.charger.pk, quantity=1)
        order = checkout(customer=self.ada)
        self.assertEqual(order.business, self.shop_b)
        self.assertIsNotNone(order.checkout_group_id)

    def test_direct_order_create_rejects_mixed_shops(self):
        with self.assertRaises(OrderFlowError):
            create_order_with_lines(customer=self.ada, lines=[
                {"product_id": self.garri.pk, "quantity": 1},
                {"product_id": self.charger.pk, "quantity": 1},
            ])

    def test_unpaid_checkout_expires_every_shop_order(self):
        self.fill_cart()
        group = checkout_cart(customer=self.ada)
        StockReservation.objects.filter(order__checkout_group=group).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(tasks.expire_unpaid_orders(), 2)
        self.assertFalse(group.orders.exclude(status=OrderStatus.CANCELLED).exists())
        self.garri.refresh_from_db()
        self.charger.refresh_from_db()
        self.assertEqual(self.garri.smartmall_allocation, 5)
        self.assertEqual(self.charger.stock, 10)


@patch("apps.payments.services.gateway.get_gateway")
class CheckoutPaymentTest(Base):

    def test_one_payment_pays_every_shop_order(self, get_gw):
        get_gw.return_value = fake_gateway()
        self.fill_cart()
        group = checkout_cart(customer=self.ada)

        payment, url = initiate_checkout_payment(checkout_group_id=group.pk, provider="paystack")
        self.assertEqual(payment.amount, Decimal("19500.00"))
        self.assertEqual(payment.checkout_group, group)
        self.assertIsNone(payment.order)
        get_gw.return_value.initiate.assert_called_once()

        confirm_payment_via_webhook(provider="paystack", external_ref="PSK-REF-1")

        for order in group.orders.all():
            self.assertEqual(order.status, OrderStatus.PAID)
            self.assertIsNotNone(order.paid_at)
            self.assertFalse(order.reservations.filter(confirmed=False).exists())
        # One "payment confirmed" notification for the one payment
        self.assertEqual(
            Notification.objects.filter(user=self.ada, title="Payment Confirmed").count(), 1
        )

    def test_one_shop_cancels_after_payment_only_that_part_is_refunded(self, get_gw):
        get_gw.return_value = fake_gateway()
        self.fill_cart()
        group = checkout_cart(customer=self.ada)
        initiate_checkout_payment(checkout_group_id=group.pk, provider="paystack")
        confirm_payment_via_webhook(provider="paystack", external_ref="PSK-REF-1")
        by_shop = self.orders_by_shop(group)

        cancel_order(order_id=by_shop[self.shop_b.pk].pk, user=self.vendor_b, reason="out_of_stock")

        a = Order.objects.get(pk=by_shop[self.shop_a.pk].pk)
        b = Order.objects.get(pk=by_shop[self.shop_b.pk].pk)
        self.assertEqual(a.status, OrderStatus.PAID)          # garri & rice still coming
        self.assertEqual(a.refund_status, RefundStatus.NONE)
        self.assertEqual(b.status, OrderStatus.CANCELLED)
        self.assertEqual(b.refund_status, RefundStatus.DUE)
        self.assertEqual(list(RefundQueue.objects.filter(refund_status=RefundStatus.DUE)), [b])

    def test_order_cancelled_before_paying_is_left_out_of_the_payment(self, get_gw):
        get_gw.return_value = fake_gateway()
        self.fill_cart()
        group = checkout_cart(customer=self.ada)
        b = self.orders_by_shop(group)[self.shop_b.pk]
        cancel_order(order_id=b.pk, user=self.ada)   # Ada drops the chargers

        payment, _ = initiate_checkout_payment(checkout_group_id=group.pk, provider="paystack")
        self.assertEqual(payment.amount, Decimal("12500.00"))

        confirm_payment_via_webhook(provider="paystack", external_ref="PSK-REF-1")
        b.refresh_from_db()
        self.assertEqual(b.status, OrderStatus.CANCELLED)
        self.assertEqual(b.refund_status, RefundStatus.NONE)  # never paid for → no refund

    def test_late_payment_after_expiry_flags_every_order_for_refund(self, get_gw):
        get_gw.return_value = fake_gateway()
        self.fill_cart()
        group = checkout_cart(customer=self.ada)
        initiate_checkout_payment(checkout_group_id=group.pk, provider="paystack")
        StockReservation.objects.filter(order__checkout_group=group).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        tasks.expire_unpaid_orders()

        confirm_payment_via_webhook(provider="paystack", external_ref="PSK-REF-1")

        for order in group.orders.all():
            self.assertEqual(order.status, OrderStatus.CANCELLED)
            self.assertEqual(order.refund_status, RefundStatus.DUE)

    def test_cannot_pay_single_order_that_belongs_to_multi_shop_checkout(self, get_gw):
        get_gw.return_value = fake_gateway()
        self.fill_cart()
        group = checkout_cart(customer=self.ada)
        a = group.orders.first()
        with self.assertRaises(ValueError):
            initiate_payment(order_id=a.pk, provider="paystack", amount=a.total)

    def test_cannot_pay_checkout_twice(self, get_gw):
        get_gw.return_value = fake_gateway()
        self.fill_cart()
        group = checkout_cart(customer=self.ada)
        payment, _ = initiate_checkout_payment(checkout_group_id=group.pk, provider="paystack")
        confirm_payment_success(payment_id=payment.pk)
        with self.assertRaises(ValueError):
            initiate_checkout_payment(checkout_group_id=group.pk, provider="paystack")


@patch("apps.payments.services.gateway.get_gateway")
class CheckoutAPITest(Base):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_full_flow_through_the_api(self, get_gw):
        get_gw.return_value = fake_gateway()
        self.client.force_authenticate(self.ada)
        self.client.post("/api/cart/add/", {"product_id": str(self.garri.pk), "quantity": 1}, format="json")
        self.client.post("/api/cart/add/", {"product_id": str(self.charger.pk), "quantity": 2}, format="json")

        res = self.client.post("/api/cart/checkout/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["order_count"], 2)
        self.assertEqual(res.data["total"], "11500.00")
        self.assertEqual(res.data["amount_due"], "11500.00")
        self.assertEqual(
            {o["business_name"] for o in res.data["orders"]},
            {"Shop ogbe-foods", "Shop cable-point-phones"},
        )
        group_id = res.data["id"]

        res = self.client.get(f"/api/checkouts/{group_id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.post(
            "/api/payments/initiate/",
            {"checkout_group_id": group_id, "provider": "paystack"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["amount"], "11500.00")
        self.assertEqual(res.data["payment_url"], "https://pay.example/x")

    def test_other_customer_cannot_see_or_pay_my_checkout(self, get_gw):
        get_gw.return_value = fake_gateway()
        self.fill_cart()
        group = checkout_cart(customer=self.ada)
        self.client.force_authenticate(make_user("eve@example.com"))
        self.assertEqual(self.client.get(f"/api/checkouts/{group.pk}/").status_code, 404)
        res = self.client.post(
            "/api/payments/initiate/",
            {"checkout_group_id": str(group.pk), "provider": "paystack"},
            format="json",
        )
        self.assertEqual(res.status_code, 404)

    def test_each_vendor_sees_only_their_own_shop_order(self, get_gw):
        self.fill_cart()
        group = checkout_cart(customer=self.ada)
        by_shop = self.orders_by_shop(group)

        self.client.force_authenticate(self.vendor_a)
        ids = [o["id"] for o in self.client.get("/api/orders/").data["results"]]
        self.assertEqual(ids, [str(by_shop[self.shop_a.pk].pk)])

        self.client.force_authenticate(self.vendor_b)
        ids = [o["id"] for o in self.client.get("/api/orders/").data["results"]]
        self.assertEqual(ids, [str(by_shop[self.shop_b.pk].pk)])
