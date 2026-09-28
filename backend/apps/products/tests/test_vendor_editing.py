"""
A shop changing its own products.

Until this worked, every price change in Asaba went through Petrus typing into
Django admin. These are the rules that keep a shop from breaking its own listing.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.products.models import Product
from apps.products.tests.test_products import make_business, make_product, make_vendor


class VendorEditsOwnProductTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = make_vendor("owner@example.com")
        self.shop = make_business(self.owner)
        self.product = make_product(self.shop, name="Rice", price="60000.00", stock=40)
        self.url = f"/api/products/{self.product.id}/"
        self.client.force_authenticate(self.owner)

    def test_change_the_price(self):
        res = self.client.patch(self.url, {"price": "72000.00"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("72000.00"))

    def test_change_the_stock(self):
        res = self.client.patch(self.url, {"stock": 12}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 12)

    def test_set_aside_some_for_check_o(self):
        res = self.client.patch(self.url, {"smartmall_allocation": 15}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.available_stock, 15)
        self.assertTrue(self.product.uses_channel_allocation)

    def test_let_check_o_sell_everything(self):
        self.product.smartmall_allocation = 15
        self.product.save()
        res = self.client.patch(self.url, {"smartmall_allocation": None}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertIsNone(self.product.smartmall_allocation)
        self.assertEqual(self.product.available_stock, 40)

    def test_cannot_set_aside_more_than_is_in_the_shop(self):
        res = self.client.patch(self.url, {"smartmall_allocation": 50}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("only have 40", str(res.data))
        self.product.refresh_from_db()
        self.assertIsNone(self.product.smartmall_allocation)

    def test_lowering_stock_below_the_allocation_is_refused(self):
        """Otherwise the shop quietly promises Check-O more than it has."""
        self.product.smartmall_allocation = 30
        self.product.save()
        res = self.client.patch(self.url, {"stock": 10}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("only have 10", str(res.data))

    def test_stock_and_allocation_can_be_lowered_together(self):
        self.product.smartmall_allocation = 30
        self.product.save()
        res = self.client.patch(
            self.url, {"stock": 10, "smartmall_allocation": 8}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.available_stock, 8)

    def test_take_it_out_of_the_shop_window(self):
        res = self.client.patch(self.url, {"is_active": False}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)

    def test_a_hidden_product_disappears_for_shoppers(self):
        self.client.patch(self.url, {"is_active": False}, format="json")
        shopper = APIClient()
        res = shopper.get(f"/api/products/?business={self.shop.id}")
        names = [p["name"] for p in res.data["results"]]
        self.assertNotIn("Rice", names)


class VendorAddsProductTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = make_vendor("adder@example.com")
        self.shop = make_business(self.owner)
        self.client.force_authenticate(self.owner)

    def test_add_a_product(self):
        res = self.client.post(
            "/api/products/",
            {
                "business": str(self.shop.id),
                "name": "Beans (white)",
                "description": "Sold by the paint rubber.",
                "price": "4500.00",
                "stock": 25,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        product = Product.objects.get(name="Beans (white)")
        self.assertEqual(product.business, self.shop)
        self.assertEqual(product.stock, 25)
        self.assertTrue(product.is_active)
        self.assertTrue(product.sku, "a product should get an SKU of its own")

    def test_add_a_product_and_set_aside_stock_in_one_go(self):
        res = self.client.post(
            "/api/products/",
            {
                "business": str(self.shop.id),
                "name": "Garri",
                "price": "3500.00",
                "stock": 30,
                "smartmall_allocation": 10,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        product = Product.objects.get(name="Garri")
        self.assertEqual(product.smartmall_allocation, 10)
        self.assertEqual(product.available_stock, 10)

    def test_cannot_set_aside_more_than_stock_when_adding(self):
        res = self.client.post(
            "/api/products/",
            {
                "business": str(self.shop.id),
                "name": "Oil",
                "price": "9000.00",
                "stock": 5,
                "smartmall_allocation": 20,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Product.objects.filter(name="Oil").exists())

    def test_cannot_add_to_someone_elses_shop(self):
        other = make_vendor("other@example.com")
        their_shop = make_business(other, slug="their-shop")
        res = self.client.post(
            "/api/products/",
            {"business": str(their_shop.id), "name": "Sneaky", "price": "1.00", "stock": 1},
            format="json",
        )
        self.assertEqual(res.status_code, 403)
        self.assertFalse(Product.objects.filter(name="Sneaky").exists())
