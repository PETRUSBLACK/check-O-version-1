"""
Channel Allocation Tests.

Tests cover:
- Setting allocation on a product
- Removing allocation
- Cart respects allocation (not total stock)
- Checkout deducts from allocation (not main stock)
- Physical store stock unaffected by SmartMall orders
- Allocation status endpoint
"""

from decimal import Decimal
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessStatus
from apps.cart.services.cart_service import add_to_cart, checkout, CartError
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


def make_product(business, name="Widget", price="1000.00", stock=100, allocation=None):
    return Product.objects.create(
        business=business, name=name, price=price,
        stock=stock, is_active=True,
        smartmall_allocation=allocation,
    )


# ─── Model Tests ───────────────────────────────────────────────────────────────

class ProductChannelAllocationModelTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)

    def test_available_stock_uses_main_stock_when_no_allocation(self):
        product = make_product(self.business, stock=50)
        self.assertEqual(product.available_stock, 50)
        self.assertFalse(product.uses_channel_allocation)

    def test_available_stock_uses_allocation_when_set(self):
        product = make_product(self.business, stock=100, allocation=20)
        self.assertEqual(product.available_stock, 20)
        self.assertTrue(product.uses_channel_allocation)

    def test_available_stock_with_zero_allocation(self):
        product = make_product(self.business, stock=100, allocation=0)
        self.assertEqual(product.available_stock, 0)
        self.assertTrue(product.uses_channel_allocation)

    def test_removing_allocation_reverts_to_main_stock(self):
        product = make_product(self.business, stock=100, allocation=20)
        product.smartmall_allocation = None
        product.save()
        self.assertEqual(product.available_stock, 100)
        self.assertFalse(product.uses_channel_allocation)


# ─── Cart Service Tests ────────────────────────────────────────────────────────

class ChannelAllocationCartTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")

    def test_cart_respects_allocation_not_total_stock(self):
        """
        Supermarket has 100 units total but only 10 allocated to SmartMall.
        Customer should not be able to order more than 10.
        """
        product = make_product(self.business, stock=100, allocation=10)
        # Should succeed — within allocation
        add_to_cart(customer=self.customer, product_id=product.pk, quantity=10)
        from apps.cart.services.cart_service import get_or_create_cart
        cart = get_or_create_cart(customer=self.customer)
        self.assertEqual(cart.items.first().quantity, 10)

    def test_cart_blocks_order_exceeding_allocation(self):
        """
        Even though total stock is 100, allocation is 10.
        Ordering 11 should fail.
        """
        product = make_product(self.business, stock=100, allocation=10)
        with self.assertRaises(CartError) as ctx:
            add_to_cart(customer=self.customer, product_id=product.pk, quantity=11)
        self.assertIn("10", str(ctx.exception))

    def test_cart_without_allocation_uses_full_stock(self):
        """Small traders without allocation can sell up to their full stock."""
        product = make_product(self.business, stock=50, allocation=None)
        add_to_cart(customer=self.customer, product_id=product.pk, quantity=50)
        from apps.cart.services.cart_service import get_or_create_cart
        cart = get_or_create_cart(customer=self.customer)
        self.assertEqual(cart.items.first().quantity, 50)


# ─── Checkout Tests ────────────────────────────────────────────────────────────

class ChannelAllocationCheckoutTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")

    def test_checkout_deducts_from_allocation_not_main_stock(self):
        """
        KEY TEST: When a vendor uses channel allocation,
        SmartMall orders must only reduce the allocation,
        NOT the main stock (which belongs to the physical store).
        """
        product = make_product(
            self.business,
            stock=100,      # Total physical store stock
            allocation=20,  # SmartMall allocation
        )

        add_to_cart(customer=self.customer, product_id=product.pk, quantity=5)
        checkout(customer=self.customer)

        product.refresh_from_db()

        # Main stock MUST remain unchanged — physical store not affected
        self.assertEqual(product.stock, 100)

        # SmartMall allocation reduced by 5
        self.assertEqual(product.smartmall_allocation, 15)

    def test_checkout_deducts_from_main_stock_when_no_allocation(self):
        """Small traders without allocation: checkout reduces main stock normally."""
        product = make_product(self.business, stock=50, allocation=None)
        add_to_cart(customer=self.customer, product_id=product.pk, quantity=3)
        checkout(customer=self.customer)

        product.refresh_from_db()
        self.assertEqual(product.stock, 47)
        self.assertIsNone(product.smartmall_allocation)

    def test_physical_store_sales_do_not_affect_smartmall_allocation(self):
        """
        Simulates a physical sale by directly reducing main stock.
        SmartMall allocation should be completely unaffected.
        """
        product = make_product(self.business, stock=100, allocation=20)

        # Simulate physical store sale — vendor's POS reduces main stock
        product.stock = 70  # 30 units sold in store
        product.save(update_fields=["stock"])

        product.refresh_from_db()

        # SmartMall allocation completely unaffected
        self.assertEqual(product.smartmall_allocation, 20)
        self.assertEqual(product.available_stock, 20)

        # SmartMall customer can still order up to 20
        add_to_cart(customer=self.customer, product_id=product.pk, quantity=20)
        from apps.cart.services.cart_service import get_or_create_cart
        cart = get_or_create_cart(customer=self.customer)
        self.assertEqual(cart.items.first().quantity, 20)


# ─── API Tests ─────────────────────────────────────────────────────────────────

class ChannelAllocationAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.product = make_product(self.business, stock=100)

    def test_vendor_can_set_allocation(self):
        self.client.force_authenticate(self.vendor)
        res = self.client.post(
            f"/api/products/{self.product.pk}/allocation/",
            {"allocation": 20},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.smartmall_allocation, 20)

    def test_vendor_can_remove_allocation(self):
        self.product.smartmall_allocation = 20
        self.product.save()
        self.client.force_authenticate(self.vendor)
        res = self.client.post(
            f"/api/products/{self.product.pk}/allocation/",
            {"allocation": None},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertIsNone(self.product.smartmall_allocation)

    def test_allocation_cannot_exceed_total_stock(self):
        self.client.force_authenticate(self.vendor)
        res = self.client.post(
            f"/api/products/{self.product.pk}/allocation/",
            {"allocation": 999},  # More than stock=100
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vendor_cannot_set_allocation_on_another_vendors_product(self):
        other_vendor = make_vendor("other@example.com")
        other_business = make_business(other_vendor, slug="other-shop")
        other_product = make_product(other_business, stock=50)
        self.client.force_authenticate(self.vendor)
        res = self.client.post(
            f"/api/products/{other_product.pk}/allocation/",
            {"allocation": 10},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_set_allocation(self):
        customer = make_user("cust@example.com")
        self.client.force_authenticate(customer)
        res = self.client.post(
            f"/api/products/{self.product.pk}/allocation/",
            {"allocation": 10},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_allocation_status_endpoint(self):
        make_product(self.business, name="Allocated Product", stock=100, allocation=20)
        make_product(self.business, name="Shared Product", stock=50, allocation=None)
        self.client.force_authenticate(self.vendor)
        res = self.client.get(f"/api/businesses/{self.business.pk}/allocation-status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("products", res.data)
        self.assertEqual(res.data["using_channel_allocation"], 1)
        self.assertEqual(res.data["using_shared_stock"], 2)  # includes base product

    def test_product_serializer_includes_available_stock(self):
        self.product.smartmall_allocation = 25
        self.product.save()
        self.client.force_authenticate(self.vendor)
        res = self.client.get(f"/api/products/{self.product.pk}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["available_stock"], 25)
        self.assertTrue(res.data["uses_channel_allocation"])
