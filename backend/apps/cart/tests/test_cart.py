from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessStatus
from apps.cart.models import Cart, CartItem
from apps.cart.services.cart_service import CartError, add_to_cart, checkout, get_or_create_cart
from apps.orders.models import Order
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


def make_product(business, name="Widget", price="10.00", stock=50, is_active=True):
    return Product.objects.create(
        business=business, name=name, price=price, stock=stock, is_active=is_active,
    )


class CartServiceTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business, stock=10)

    def test_get_or_create_cart_creates_for_new_customer(self):
        cart = get_or_create_cart(customer=self.customer)
        self.assertIsNotNone(cart.pk)
        self.assertEqual(cart.customer, self.customer)

    def test_get_or_create_cart_returns_same_cart(self):
        cart1 = get_or_create_cart(customer=self.customer)
        cart2 = get_or_create_cart(customer=self.customer)
        self.assertEqual(cart1.pk, cart2.pk)

    def test_add_to_cart_creates_item(self):
        add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=2)
        cart = get_or_create_cart(customer=self.customer)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 2)

    def test_add_to_cart_increments_existing_item(self):
        add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=2)
        add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=3)
        cart = get_or_create_cart(customer=self.customer)
        self.assertEqual(cart.items.first().quantity, 5)

    def test_add_to_cart_respects_stock_limit(self):
        with self.assertRaises(CartError):
            add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=999)

    def test_add_inactive_product_raises_error(self):
        inactive = make_product(self.business, name="Inactive", stock=10, is_active=False)
        with self.assertRaises(CartError):
            add_to_cart(customer=self.customer, product_id=inactive.pk, quantity=1)

    def test_cart_total_is_correct(self):
        product2 = make_product(self.business, name="Gadget", price="25.00", stock=10)
        add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=2)
        add_to_cart(customer=self.customer, product_id=product2.pk, quantity=1)
        cart = get_or_create_cart(customer=self.customer)
        # 2 x 10.00 + 1 x 25.00 = 45.00
        from decimal import Decimal
        self.assertEqual(cart.total, Decimal("45.00"))


class CheckoutServiceTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business, price="20.00", stock=10)

    def test_checkout_creates_order(self):
        add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=2)
        order = checkout(customer=self.customer)
        self.assertIsNotNone(order.pk)
        self.assertEqual(order.customer, self.customer)

    def test_checkout_deducts_stock(self):
        add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=3)
        checkout(customer=self.customer)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)

    def test_checkout_clears_cart(self):
        add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=1)
        checkout(customer=self.customer)
        cart = get_or_create_cart(customer=self.customer)
        self.assertEqual(cart.items.count(), 0)

    def test_checkout_calculates_correct_total(self):
        from decimal import Decimal
        add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=2)
        order = checkout(customer=self.customer)
        self.assertEqual(order.total, Decimal("40.00"))

    def test_checkout_empty_cart_raises_error(self):
        with self.assertRaises(CartError):
            checkout(customer=self.customer)

    def test_checkout_insufficient_stock_raises_error(self):
        add_to_cart(customer=self.customer, product_id=self.product.pk, quantity=5)
        # Drain the stock from another path
        self.product.stock = 2
        self.product.save()
        with self.assertRaises(CartError):
            checkout(customer=self.customer)


class CartAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business, stock=20)

    def test_get_cart_returns_empty_cart(self):
        self.client.force_authenticate(self.customer)
        res = self.client.get("/api/cart/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["item_count"], 0)

    def test_add_to_cart(self):
        self.client.force_authenticate(self.customer)
        res = self.client.post("/api/cart/add/", {
            "product_id": str(self.product.pk), "quantity": 3
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["item_count"], 1)

    def test_vendor_cannot_add_to_cart(self):
        self.client.force_authenticate(self.vendor)
        res = self.client.post("/api/cart/add/", {
            "product_id": str(self.product.pk), "quantity": 1
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_add_to_cart(self):
        res = self.client.post("/api/cart/add/", {
            "product_id": str(self.product.pk), "quantity": 1
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_cart_item(self):
        self.client.force_authenticate(self.customer)
        self.client.post("/api/cart/add/", {"product_id": str(self.product.pk), "quantity": 2}, format="json")
        res = self.client.patch("/api/cart/update/", {"product_id": str(self.product.pk), "quantity": 5}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["items"][0]["quantity"], 5)

    def test_remove_from_cart(self):
        self.client.force_authenticate(self.customer)
        self.client.post("/api/cart/add/", {"product_id": str(self.product.pk), "quantity": 1}, format="json")
        res = self.client.delete(f"/api/cart/remove/{self.product.pk}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["item_count"], 0)

    def test_checkout_returns_order(self):
        self.client.force_authenticate(self.customer)
        self.client.post("/api/cart/add/", {"product_id": str(self.product.pk), "quantity": 1}, format="json")
        res = self.client.post("/api/cart/checkout/")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", res.data)
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 1)

    def test_checkout_empty_cart_returns_400(self):
        self.client.force_authenticate(self.customer)
        res = self.client.post("/api/cart/checkout/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
