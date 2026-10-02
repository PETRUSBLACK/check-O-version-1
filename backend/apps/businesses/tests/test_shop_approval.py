"""
Getting a shop from "I just signed up" to "customers can see me".

The lifecycle itself was already here. What was missing was everyone being told
anything about it — a shop could be submitted, approved or rejected in total
silence, which from the vendor's side is indistinguishable from the app being
broken. These tests are mostly about who hears what, and when.
"""

from decimal import Decimal

from django.test import TestCase

from apps.businesses.choices import BusinessCategory, BusinessStatus
from apps.businesses.models import Business, BusinessLocation
from apps.businesses.services.registration import (
    BusinessFlowError,
    approve_business,
    missing_before_review,
    register_business,
    reject_business,
    submit_business_for_review,
)
from apps.notifications.models import Notification
from apps.products.models import Product
from apps.users.models import User, UserRole


class ShopApprovalTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="trader@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.reviewer = User.objects.create_user(
            email="petrus@example.com", password="testpass12345", role=UserRole.ADMIN
        )
        self.reviewer.is_staff = True
        self.reviewer.save(update_fields=["is_staff"])

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def a_shop(self, **extra):
        return register_business(
            owner=self.owner,
            name=extra.pop("name", "Mama Ngozi Provisions"),
            category=extra.pop("category", BusinessCategory.RETAIL),
            **extra,
        )

    def finish(self, shop, *, product=True):
        shop.business_phone = "08031234567"
        shop.address = "12 Nnebisi Road, Asaba"
        shop.save(update_fields=["business_phone", "address", "updated_at"])
        BusinessLocation.objects.update_or_create(
            business=shop,
            defaults={
                "address": "12 Nnebisi Road, Asaba",
                "city": "Asaba",
                "state": "Delta",
                "latitude": Decimal("6.2003000"),
                "longitude": Decimal("6.7331000"),
            },
        )
        if product:
            Product.objects.create(
                business=shop, name="Rice 50kg", price=Decimal("68000"), stock=4, is_active=True
            )
        shop.refresh_from_db()
        return shop

    def messages_for(self, user):
        return list(Notification.objects.filter(user=user).order_by("created_at"))

    # ─── A new shop starts out of sight ───────────────────────────────────────

    def test_a_new_shop_starts_as_draft(self):
        """
        Nobody has looked at it yet, so no shopper should see it. The vendor can
        still fill it in — that is the point of draft rather than a locked queue.
        """
        self.assertEqual(self.a_shop().status, BusinessStatus.DRAFT)

    def test_a_shop_does_not_need_a_slug_or_a_cac_number(self):
        """
        A trader in Ogbeogonogo market has no CAC certificate and should not be
        inventing a web address for herself. The slug comes from the name.
        """
        shop = self.a_shop(name="Chidi & Sons Electronics")
        self.assertTrue(shop.slug)
        self.assertEqual(shop.registration_number, "")
        self.assertEqual(shop.legal_name, "")

    # ─── What it still needs ──────────────────────────────────────────────────

    def test_a_bare_shop_is_missing_everything_a_reviewer_needs(self):
        missing = missing_before_review(self.a_shop())
        joined = " ".join(missing).lower()
        self.assertIn("phone", joined)
        self.assertIn("address", joined)
        self.assertIn("map", joined)
        self.assertIn("product", joined)

    def test_a_finished_shop_is_missing_nothing(self):
        self.assertEqual(missing_before_review(self.finish(self.a_shop())), [])

    def test_a_shop_with_no_products_is_not_ready(self):
        """
        An approved shop with an empty shelf is a dead end for every shopper who
        taps it, and they do not come back twice.
        """
        shop = self.finish(self.a_shop(), product=False)
        self.assertEqual(
            missing_before_review(shop), ["At least one product for sale"]
        )

    def test_a_hidden_product_does_not_count(self):
        shop = self.finish(self.a_shop(), product=False)
        Product.objects.create(
            business=shop, name="Draft item", price=Decimal("500"), stock=1, is_active=False
        )
        self.assertEqual(
            missing_before_review(shop), ["At least one product for sale"]
        )

    def test_submitting_an_unfinished_shop_is_refused_with_the_reasons(self):
        shop = self.a_shop()
        with self.assertRaises(BusinessFlowError) as caught:
            submit_business_for_review(business_id=shop.pk)
        self.assertIn("phone", str(caught.exception).lower())
        shop.refresh_from_db()
        self.assertEqual(shop.status, BusinessStatus.DRAFT)

    # ─── Submitting ───────────────────────────────────────────────────────────

    def test_submitting_moves_it_to_pending_and_tells_the_reviewers(self):
        shop = self.finish(self.a_shop())
        submit_business_for_review(business_id=shop.pk)

        shop.refresh_from_db()
        self.assertEqual(shop.status, BusinessStatus.PENDING)
        self.assertIsNotNone(shop.submitted_for_review_at)

        told = self.messages_for(self.reviewer)
        self.assertEqual(len(told), 1)
        self.assertIn("waiting for review", told[0].title.lower())
        self.assertIn(shop.name, told[0].body)
        self.assertIn(self.owner.email, told[0].body)

    def test_a_customer_is_not_told_about_shops_waiting_for_review(self):
        shopper = User.objects.create_user(
            email="shopper@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        submit_business_for_review(business_id=self.finish(self.a_shop()).pk)
        self.assertEqual(self.messages_for(shopper), [])

    def test_a_shop_already_waiting_cannot_be_submitted_again(self):
        shop = self.finish(self.a_shop())
        submit_business_for_review(business_id=shop.pk)
        with self.assertRaises(BusinessFlowError):
            submit_business_for_review(business_id=shop.pk)

    # ─── Approving ────────────────────────────────────────────────────────────

    def test_approving_puts_the_shop_in_front_of_shoppers_and_says_so(self):
        shop = self.finish(self.a_shop())
        submit_business_for_review(business_id=shop.pk)
        approve_business(business_id=shop.pk)

        shop.refresh_from_db()
        self.assertEqual(shop.status, BusinessStatus.APPROVED)
        self.assertIsNotNone(shop.verified_at)

        told = self.messages_for(self.owner)
        self.assertEqual(len(told), 1)
        self.assertIn(shop.name, told[0].title)
        self.assertIn("open on check-o", told[0].title.lower())

    def test_a_shop_cannot_be_approved_before_it_is_submitted(self):
        shop = self.finish(self.a_shop())
        with self.assertRaises(BusinessFlowError):
            approve_business(business_id=shop.pk)
        self.assertEqual(self.messages_for(self.owner), [])

    def test_approving_twice_is_refused(self):
        shop = self.finish(self.a_shop())
        submit_business_for_review(business_id=shop.pk)
        approve_business(business_id=shop.pk)
        with self.assertRaises(BusinessFlowError):
            approve_business(business_id=shop.pk)
        # And the owner is not congratulated a second time.
        self.assertEqual(len(self.messages_for(self.owner)), 1)

    # ─── Rejecting ────────────────────────────────────────────────────────────

    def test_rejecting_sends_the_reason_word_for_word(self):
        """
        A vendor told only "rejected" either gives up or resubmits the same thing.
        The reason has to travel with the refusal.
        """
        shop = self.finish(self.a_shop())
        submit_business_for_review(business_id=shop.pk)
        reject_business(
            business_id=shop.pk,
            reason="The phone number does not connect. Send a number that rings.",
        )

        shop.refresh_from_db()
        self.assertEqual(shop.status, BusinessStatus.REJECTED)

        told = self.messages_for(self.owner)
        self.assertEqual(len(told), 1)
        self.assertIn("does not connect", told[0].body)
        self.assertIn("submit your shop again", told[0].body.lower())

    def test_a_rejection_needs_a_reason(self):
        shop = self.finish(self.a_shop())
        submit_business_for_review(business_id=shop.pk)
        with self.assertRaises(BusinessFlowError):
            reject_business(business_id=shop.pk, reason="   ")

    def test_a_rejected_shop_can_be_fixed_and_resubmitted(self):
        shop = self.finish(self.a_shop())
        submit_business_for_review(business_id=shop.pk)
        reject_business(business_id=shop.pk, reason="Wrong address.")

        shop.refresh_from_db()
        shop.address = "14 Nnebisi Road, Asaba"
        shop.save(update_fields=["address", "updated_at"])

        submit_business_for_review(business_id=shop.pk)
        shop.refresh_from_db()
        self.assertEqual(shop.status, BusinessStatus.PENDING)
        # The old refusal is cleared, so the app stops showing a stale complaint.
        self.assertEqual(shop.rejection_reason, "")

    # ─── A shop still waiting is invisible ────────────────────────────────────

    def test_only_approved_shops_are_visible_to_a_shopper(self):
        waiting = self.finish(self.a_shop())
        submit_business_for_review(business_id=waiting.pk)

        live = self.finish(
            self.a_shop(name="Open Already", address="9 Summit Road, Asaba")
        )
        submit_business_for_review(business_id=live.pk)
        approve_business(business_id=live.pk)

        visible = Business.objects.filter(status=BusinessStatus.APPROVED)
        self.assertIn(live, visible)
        self.assertNotIn(waiting, visible)


class AdminApprovalQueueTest(TestCase):
    """
    Petrus approves shops from Django admin, not from the app. A template that
    does not render is a feature that does not exist, and a template only fails
    when someone loads it — so load it here.
    """

    def setUp(self):
        self.reviewer = User.objects.create_superuser(
            email="boss@example.com", password="testpass12345"
        )
        self.owner = User.objects.create_user(
            email="shopowner@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.client.force_login(self.reviewer)

    def a_waiting_shop(self, name="Waiting Shop", slug="waiting-shop"):
        shop = Business.objects.create(
            owner=self.owner,
            name=name,
            slug=slug,
            category=BusinessCategory.RETAIL,
            status=BusinessStatus.DRAFT,
            business_phone="08031234567",
            address="12 Nnebisi Road, Asaba",
        )
        BusinessLocation.objects.create(
            business=shop,
            address="12 Nnebisi Road, Asaba",
            city="Asaba",
            state="Delta",
            latitude=Decimal("6.2003000"),
            longitude=Decimal("6.7331000"),
        )
        Product.objects.create(
            business=shop, name="Rice", price=Decimal("68000"), stock=4, is_active=True
        )
        submit_business_for_review(business_id=shop.pk)
        shop.refresh_from_db()
        return shop

    def test_the_shop_list_opens(self):
        self.a_waiting_shop()
        res = self.client.get("/admin/businesses/business/")
        self.assertEqual(res.status_code, 200)

    def test_approving_from_the_list_takes_the_shop_live(self):
        shop = self.a_waiting_shop()
        res = self.client.post(
            "/admin/businesses/business/",
            {"action": "approve_shops", "_selected_action": [str(shop.pk)]},
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        shop.refresh_from_db()
        self.assertEqual(shop.status, BusinessStatus.APPROVED)
        self.assertTrue(Notification.objects.filter(user=self.owner).exists())

    def test_rejecting_asks_for_a_reason_first(self):
        shop = self.a_waiting_shop()
        res = self.client.post(
            "/admin/businesses/business/",
            {"action": "reject_shops", "_selected_action": [str(shop.pk)]},
        )
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "What does this shop need to fix?")
        # Nothing has happened yet — the reason has not been given.
        shop.refresh_from_db()
        self.assertEqual(shop.status, BusinessStatus.PENDING)

    def test_rejecting_with_a_reason_sends_it_to_the_owner(self):
        shop = self.a_waiting_shop()
        res = self.client.post(
            "/admin/businesses/business/",
            {
                "action": "reject_shops",
                "_selected_action": [str(shop.pk)],
                "apply": "1",
                "reason": "Your address is outside Asaba for now.",
            },
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        shop.refresh_from_db()
        self.assertEqual(shop.status, BusinessStatus.REJECTED)
        message = Notification.objects.get(user=self.owner)
        self.assertIn("outside Asaba", message.body)

    def test_approving_a_shop_that_was_never_submitted_is_reported_not_silent(self):
        shop = Business.objects.create(
            owner=self.owner,
            name="Not Submitted",
            slug="not-submitted",
            category=BusinessCategory.RETAIL,
            status=BusinessStatus.DRAFT,
        )
        res = self.client.post(
            "/admin/businesses/business/",
            {"action": "approve_shops", "_selected_action": [str(shop.pk)]},
            follow=True,
        )
        self.assertContains(res, "Not Submitted")
        shop.refresh_from_db()
        self.assertEqual(shop.status, BusinessStatus.DRAFT)


class ShopSignUpApiTest(TestCase):
    """
    What the app actually sends when a vendor sets their shop up. The old
    serializer demanded a slug, a legal name and a registration number, which
    nobody standing in Ogbeogonogo market has.
    """

    def setUp(self):
        from rest_framework.test import APIClient

        self.api = APIClient()
        self.vendor = User.objects.create_user(
            email="newtrader@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.api.force_authenticate(self.vendor)

    def test_a_vendor_can_create_a_shop_with_just_a_name_and_a_category(self):
        res = self.api.post(
            "/api/businesses/",
            {
                "name": "Mama Ngozi Provisions",
                "category": BusinessCategory.SUPERMARKET,
                "business_phone": "08031234567",
                "address": "12 Nnebisi Road, Asaba",
                "delivers": True,
                "delivery_fee": "500.00",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)

        shop = Business.objects.get(owner=self.vendor)
        self.assertEqual(shop.status, BusinessStatus.DRAFT)
        self.assertTrue(shop.slug, "the slug should be worked out from the name")
        self.assertTrue(shop.delivers)
        self.assertEqual(str(shop.delivery_fee), "500.00")

    def test_two_shops_with_the_same_name_both_get_a_usable_slug(self):
        other = User.objects.create_user(
            email="rival@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.api.post("/api/businesses/", {"name": "City Mart", "category": "retail"}, format="json")
        self.api.force_authenticate(other)
        res = self.api.post(
            "/api/businesses/", {"name": "City Mart", "category": "retail"}, format="json"
        )
        self.assertEqual(res.status_code, 201, res.data)
        slugs = set(Business.objects.values_list("slug", flat=True))
        self.assertEqual(len(slugs), 2, slugs)

    def test_a_shopper_cannot_open_a_shop(self):
        shopper = User.objects.create_user(
            email="justshopping@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.api.force_authenticate(shopper)
        res = self.api.post(
            "/api/businesses/", {"name": "Sneaky Shop", "category": "retail"}, format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_mine_lists_a_draft_shop_with_what_it_still_needs(self):
        self.api.post(
            "/api/businesses/",
            {"name": "Half Done", "category": "retail"},
            format="json",
        )
        res = self.api.get("/api/businesses/mine/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        shop = res.data[0]
        self.assertEqual(shop["status"], BusinessStatus.DRAFT)
        self.assertTrue(shop["missing_before_review"])

    def test_the_pin_on_the_map_can_be_set_and_comes_back(self):
        created = self.api.post(
            "/api/businesses/",
            {"name": "Pinned Shop", "category": "retail"},
            format="json",
        )
        shop_id = created.data["id"]

        res = self.api.post(
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
        self.assertEqual(res.status_code, 200, res.data)

        mine = self.api.get("/api/businesses/mine/").data[0]
        self.assertAlmostEqual(mine["latitude"], 6.2003, places=4)
        self.assertAlmostEqual(mine["longitude"], 6.7331, places=4)
        self.assertNotIn(
            "Where your shop is on the map, so nearby customers find you",
            mine["missing_before_review"],
        )

    def test_another_vendor_cannot_move_my_shop_on_the_map(self):
        created = self.api.post(
            "/api/businesses/", {"name": "Mine Alone", "category": "retail"}, format="json"
        )
        shop_id = created.data["id"]

        intruder = User.objects.create_user(
            email="intruder@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.api.force_authenticate(intruder)
        res = self.api.post(
            f"/api/businesses/{shop_id}/location/",
            {
                "latitude": "6.5",
                "longitude": "3.3",
                "city": "Lagos",
                "state": "Lagos",
                "full_address": "Somewhere else entirely",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 404)

    def test_a_shopper_does_not_get_told_what_a_shop_is_missing(self):
        """It is none of their business, and working it out costs a query."""
        created = self.api.post(
            "/api/businesses/", {"name": "Private Business", "category": "retail"}, format="json"
        )
        shopper = User.objects.create_user(
            email="nosy@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.api.force_authenticate(shopper)
        res = self.api.get(f"/api/businesses/{created.data['id']}/")
        if res.status_code == 200:
            self.assertEqual(res.data["missing_before_review"], [])
