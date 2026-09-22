"""
A shop's cost price, real stock count and Check-O allocation are the shop's own
business. Customers must never see them; the owner and admins must still get them.
"""

from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.products.serializers.product import ProductSerializer, VENDOR_ONLY_FIELDS
from apps.products.tests.test_products import make_business, make_product, make_user, make_vendor
from apps.users.models import UserRole


class ProductPrivateFieldsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor("owner@example.com")
        self.business = make_business(self.vendor)
        self.product = make_product(self.business, name="Rice 50kg", price="62000.00", stock=40)
        self.product.cost_price = "51000.00"
        self.product.smartmall_allocation = 12
        self.product.low_stock_threshold = 5
        self.product.save()
        self.url = f"/api/products/{self.product.id}/"

    def test_anonymous_visitor_cannot_see_private_fields(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        for field in VENDOR_ONLY_FIELDS:
            self.assertNotIn(field, res.data, f"{field} leaked to an anonymous visitor")

    def test_customer_cannot_see_private_fields(self):
        self.client.force_authenticate(make_user("buyer@example.com"))
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        for field in VENDOR_ONLY_FIELDS:
            self.assertNotIn(field, res.data, f"{field} leaked to a customer")

    def test_customer_still_sees_what_they_need(self):
        self.client.force_authenticate(make_user("buyer2@example.com"))
        res = self.client.get(self.url)
        self.assertEqual(res.data["name"], "Rice 50kg")
        self.assertEqual(res.data["price"], "62000.00")
        # 12 allocated out of 40 in stock -> 12 is what Check-O can sell.
        self.assertEqual(res.data["available_stock"], 12)
        self.assertTrue(res.data["uses_channel_allocation"])

    def test_another_vendor_cannot_reach_the_product_at_all(self):
        """A signed-in vendor only sees their own catalogue, so this is a 404."""
        other = make_vendor("other@example.com")
        make_business(other, slug="other-shop")
        self.client.force_authenticate(other)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 404)

    def test_serializer_hides_private_fields_from_a_different_vendor(self):
        """Belt and braces: even if such a product reached them, the numbers are stripped."""
        other = make_vendor("other2@example.com")
        make_business(other, slug="other-shop-2")
        request = APIRequestFactory().get(self.url)
        request.user = other
        data = ProductSerializer(self.product, context={"request": Request(request)}).data
        for field in VENDOR_ONLY_FIELDS:
            self.assertNotIn(field, data, f"{field} leaked to a different vendor")

    def test_owner_sees_private_fields(self):
        self.client.force_authenticate(self.vendor)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        for field in VENDOR_ONLY_FIELDS:
            self.assertIn(field, res.data, f"{field} hidden from the shop owner")
        self.assertEqual(res.data["cost_price"], "51000.00")
        self.assertEqual(res.data["stock"], 40)

    def test_admin_sees_private_fields(self):
        admin = make_user("admin@example.com", role=UserRole.ADMIN)
        self.client.force_authenticate(admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("cost_price", res.data)


class AvailableStockMatchesModelTest(TestCase):
    """The API number must be the same number the checkout uses."""

    def setUp(self):
        self.client = APIClient()
        vendor = make_vendor("owner2@example.com")
        self.business = make_business(vendor, slug="stock-shop")

    def _available_from_api(self, product):
        res = self.client.get(f"/api/products/{product.id}/")
        return res.data["available_stock"]

    def test_no_allocation_uses_main_stock(self):
        product = make_product(self.business, name="Garri", stock=30)
        self.assertEqual(self._available_from_api(product), 30)
        self.assertEqual(product.available_stock, 30)

    def test_allocation_below_stock_wins(self):
        product = make_product(self.business, name="Beans", stock=30)
        product.smartmall_allocation = 8
        product.save()
        self.assertEqual(self._available_from_api(product), 8)

    def test_allocation_above_stock_is_capped_by_stock(self):
        """The shop sold 25 of 30 in person; the old API still promised 20 online."""
        product = make_product(self.business, name="Oil", stock=5)
        product.smartmall_allocation = 20
        product.save()
        self.assertEqual(product.available_stock, 5)
        self.assertEqual(self._available_from_api(product), 5)
