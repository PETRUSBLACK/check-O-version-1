"""
A brand new shop has to be able to put something on its shelf.

This file exists because of a deadlock that shipped to production and was found
by a person, not by a test:

    - a shop cannot be submitted for review until it has at least one product
      (missing_before_review)
    - a shop cannot be approved until it has been submitted
    - and product creation used to refuse any shop that was not already approved

So every vendor who signed up was stuck, permanently, with no explanation. The
app told her she needed a product; the server told her she needed approval.

The reason no test caught it is worth remembering: every existing test built its
products with `Product.objects.create(...)`, straight through the ORM, which
never touches the view's permission check. The tests below go through the API the
way the app does. When a rule lives in a view, only a request can prove it.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.businesses.choices import BusinessCategory, BusinessStatus
from apps.businesses.models import Business
from apps.products.models import Product
from apps.users.models import User, UserRole


class NewShopCanListProductsTest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(
            email="newvendor@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.api.force_authenticate(self.owner)

    def a_shop(self, status=BusinessStatus.DRAFT, slug="new-shop"):
        return Business.objects.create(
            owner=self.owner,
            name=f"Shop {slug}",
            slug=slug,
            category=BusinessCategory.RETAIL,
            status=status,
        )

    def post_product(self, shop, name="Bag of rice"):
        return self.api.post(
            "/api/products/",
            {
                "business": str(shop.pk),
                "name": name,
                "price": "68000.00",
                "stock": 10,
            },
            format="json",
        )

    # ─── The deadlock ─────────────────────────────────────────────────────────

    def test_a_draft_shop_can_add_a_product(self):
        """
        The one that was broken. Without this a new vendor can never get out of
        draft, because the review checklist demands a product she cannot create.
        """
        res = self.post_product(self.a_shop())
        self.assertEqual(res.status_code, 201, res.data)

    def test_a_shop_waiting_for_review_can_still_add_products(self):
        """
        Waiting is not meant to be dead time — she should be filling her shelf
        while Check-O looks at her shop.
        """
        res = self.post_product(self.a_shop(status=BusinessStatus.PENDING, slug="pending-shop"))
        self.assertEqual(res.status_code, 201, res.data)

    def test_a_rejected_shop_can_fix_itself(self):
        """Being turned down must leave her able to put it right."""
        res = self.post_product(self.a_shop(status=BusinessStatus.REJECTED, slug="rejected-shop"))
        self.assertEqual(res.status_code, 201, res.data)

    def test_an_approved_shop_can_add_products(self):
        res = self.post_product(self.a_shop(status=BusinessStatus.APPROVED, slug="live-shop"))
        self.assertEqual(res.status_code, 201, res.data)

    def test_a_suspended_shop_cannot(self):
        """The one status that still refuses — a shop taken down should not restock."""
        res = self.post_product(self.a_shop(status=BusinessStatus.SUSPENDED, slug="paused-shop"))
        self.assertEqual(res.status_code, 403)

    # ─── Nothing leaks ────────────────────────────────────────────────────────

    def test_a_draft_shops_products_are_invisible_to_shoppers(self):
        """
        Letting an unapproved shop list products only works because shoppers
        cannot see them. If this breaks, the approval gate is worthless.
        """
        shop = self.a_shop()
        self.post_product(shop, name="Not live yet")

        shopper = User.objects.create_user(
            email="shopper@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.api.force_authenticate(shopper)
        listed = self.api.get("/api/products/").data
        names = [p["name"] for p in (listed.get("results", listed) if isinstance(listed, dict) else listed)]
        self.assertNotIn("Not live yet", names)

    def test_the_owner_can_see_her_own_draft_products(self):
        shop = self.a_shop()
        self.post_product(shop, name="Mine to see")
        listed = self.api.get("/api/products/", {"business": str(shop.pk)}).data
        names = [p["name"] for p in (listed.get("results", listed) if isinstance(listed, dict) else listed)]
        self.assertIn("Mine to see", names)

    def test_another_vendor_cannot_add_to_my_shop(self):
        shop = self.a_shop()
        intruder = User.objects.create_user(
            email="intruder2@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.api.force_authenticate(intruder)
        res = self.post_product(shop, name="Sneaky")
        self.assertEqual(res.status_code, 403)
        self.assertFalse(Product.objects.filter(name="Sneaky").exists())

    # ─── The whole way out of draft, through the API ──────────────────────────

    def test_a_new_vendor_can_get_from_signup_to_submitted(self):
        """
        End to end, the way the app does it: create the shop, fill it in, add a
        product, submit. If any link in that chain refuses, a vendor is stuck.
        """
        created = self.api.post(
            "/api/businesses/",
            {
                "name": "Mama Ngozi Provisions",
                "category": BusinessCategory.SUPERMARKET,
                "business_phone": "08031234567",
                "address": "12 Nnebisi Road, Asaba",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        shop_id = created.data["id"]

        placed = self.api.post(
            f"/api/businesses/{shop_id}/location/",
            {
                "latitude": "6.2003000",
                "longitude": "6.7331000",
                "city": "Asaba",
                "state": "Delta",
                "full_address": "12 Nnebisi Road, Asaba",
            },
            format="json",
        )
        self.assertEqual(placed.status_code, 200, placed.data)

        stocked = self.api.post(
            "/api/products/",
            {"business": shop_id, "name": "Rice 50kg", "price": "68000.00", "stock": 4},
            format="json",
        )
        self.assertEqual(stocked.status_code, 201, stocked.data)

        sent = self.api.post(f"/api/businesses/{shop_id}/submit-for-review/")
        self.assertEqual(sent.status_code, 200, sent.data)

        mine = self.api.get("/api/businesses/mine/").data[0]
        self.assertEqual(mine["status"], BusinessStatus.PENDING)
        self.assertEqual(mine["missing_before_review"], [])
