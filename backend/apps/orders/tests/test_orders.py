from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessStatus
from apps.cart.services.cart_service import add_to_cart, checkout
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.orders.services.order_service import OrderFlowError, transition_order_status
from apps.products.models import Product
from apps.users.models import User, UserRole


def make_user(email, role=UserRole.CUSTOMER, password="testpass12345"):
    return User.objects.create_user(email=email, password=password, role=role)


def make_vendor(email="vendor@example.com"):
    return make_user(email, role=UserRole.VENDOR)


def make_business(owner, slug="test-shop"):
    return Business.objects.create(
        owner=owner, name="Test Shop", slug=slug,
        legal_name="Test Ltd", registration_number="RC1234567",
        status=BusinessStatus.APPROVED,
    )


def make_product(business, price="15.00", stock=20):
    return Product.objects.create(
        business=business, name="Widget", price=price, stock=stock, is_active=True,
    )


def make_order(customer, product, quantity=1):
    add_to_cart(customer=customer, product_id=product.pk, quantity=quantity)
    return checkout(customer=customer)


class OrderServiceTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)

    def test_checkout_creates_order_with_pending_payment_status(self):
        order = make_order(self.customer, self.product, quantity=2)
        self.assertEqual(order.status, OrderStatus.PENDING_PAYMENT)

    def test_order_total_is_correct(self):
        order = make_order(self.customer, self.product, quantity=3)
        self.assertEqual(order.total, Decimal("45.00"))

    def test_order_has_correct_line_items(self):
        order = make_order(self.customer, self.product, quantity=2)
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal("15.00"))

    def test_transition_pending_to_paid(self):
        order = make_order(self.customer, self.product)
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PAID)

    def test_transition_paid_to_processing(self):
        order = make_order(self.customer, self.product)
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PROCESSING.value)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PROCESSING)

    def test_invalid_transition_raises_error(self):
        order = make_order(self.customer, self.product)
        with self.assertRaises(OrderFlowError):
            # Can't go from pending_payment directly to delivered
            transition_order_status(order_id=order.pk, to_status=OrderStatus.DELIVERED.value)

    def test_customer_can_cancel_pending_order(self):
        order = make_order(self.customer, self.product)
        transition_order_status(order_id=order.pk, to_status=OrderStatus.CANCELLED.value)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_cannot_transition_cancelled_order(self):
        order = make_order(self.customer, self.product)
        transition_order_status(order_id=order.pk, to_status=OrderStatus.CANCELLED.value)
        with self.assertRaises(OrderFlowError):
            transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)


class OrderAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)

    def test_customer_can_list_own_orders(self):
        make_order(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_customer_cannot_see_another_customers_orders(self):
        customer2 = make_user("other@example.com")
        make_order(customer2, self.product)
        self.client.force_authenticate(self.customer)
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 0)

    def test_unauthenticated_cannot_list_orders(self):
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_can_cancel_own_order(self):
        order = make_order(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        res = self.client.post(f"/api/orders/{order.pk}/transition/", {"status": "cancelled"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_customer_cannot_transition_to_paid(self):
        order = make_order(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        res = self.client.post(f"/api/orders/{order.pk}/transition/", {"status": "paid"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_vendor_can_see_orders_containing_their_products(self):
        make_order(self.customer, self.product)
        self.client.force_authenticate(self.vendor)
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data["results"]), 1)
