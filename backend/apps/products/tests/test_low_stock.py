"""
Telling a shop when something is running out.

The behaviour that matters is not "does it detect low stock" — that part is a
comparison. It is the restraint: a checker that runs every five minutes must not
say the same thing 288 times a day, and a shop with eight low items must not get
eight separate messages. Those are the tests that stop this becoming the feature
vendors turn off.
"""

from decimal import Decimal

from django.test import TestCase

from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.notifications.models import Notification
from apps.products.models import Product
from apps.products.services.low_stock import check_low_stock
from apps.users.models import User, UserRole


class LowStockTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="lowstock@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.shop = Business.objects.create(
            owner=self.owner,
            name="Corner Shop",
            slug="corner-shop-low",
            legal_name="Corner Shop Ltd",
            registration_number="RC5550001",
            status=BusinessStatus.APPROVED,
        )

    def a_product(self, name, stock, threshold=5, allocation=None, active=True):
        return Product.objects.create(
            business=self.shop,
            name=name,
            price=Decimal("1000.00"),
            stock=stock,
            smartmall_allocation=allocation,
            low_stock_threshold=threshold,
            is_active=active,
        )

    def messages(self):
        return list(
            Notification.objects.filter(user=self.owner).order_by("created_at")
        )

    # ─── It notices ───────────────────────────────────────────────────────────

    def test_a_product_at_the_threshold_is_reported(self):
        self.a_product("Rice", stock=5, threshold=5)
        self.assertEqual(check_low_stock(), 1)
        msgs = self.messages()
        self.assertEqual(len(msgs), 1)
        self.assertIn("Rice", msgs[0].title)
        self.assertIn("5 left", msgs[0].body)

    def test_a_product_above_its_threshold_is_left_alone(self):
        self.a_product("Rice", stock=6, threshold=5)
        self.assertEqual(check_low_stock(), 0)
        self.assertEqual(self.messages(), [])

    def test_a_finished_product_is_worded_differently(self):
        self.a_product("Beans", stock=0, threshold=5)
        check_low_stock()
        msg = self.messages()[0]
        self.assertIn("finished", msg.title.lower())
        self.assertIn("none left", msg.body.lower())

    def test_the_check_o_portion_is_what_counts(self):
        """
        A shop with 40 bags but only 3 set aside for Check-O is low *on Check-O*,
        and that is the portion that can vanish without her noticing.
        """
        self.a_product("Semovita", stock=40, allocation=3, threshold=5)
        self.assertEqual(check_low_stock(), 1)
        self.assertIn("3 left", self.messages()[0].body)

    # ─── The restraint ────────────────────────────────────────────────────────

    def test_it_does_not_repeat_while_the_item_stays_low(self):
        """The whole point. Five minutes apart, 288 times a day."""
        self.a_product("Rice", stock=2, threshold=5)
        check_low_stock()
        for _ in range(5):
            self.assertEqual(check_low_stock(), 0)
        self.assertEqual(len(self.messages()), 1)

    def test_it_speaks_again_after_a_restock_and_another_fall(self):
        product = self.a_product("Rice", stock=2, threshold=5)
        check_low_stock()
        self.assertEqual(len(self.messages()), 1)

        # Restocked above the line: the earlier warning is forgotten.
        product.stock = 50
        product.save(update_fields=["stock"])
        check_low_stock()
        product.refresh_from_db()
        self.assertIsNone(product.low_stock_notified_at)

        # And falls again.
        product.stock = 1
        product.save(update_fields=["stock"])
        check_low_stock()
        self.assertEqual(len(self.messages()), 2)

    def test_eight_low_items_are_one_message_not_eight(self):
        for i in range(8):
            self.a_product(f"Item {i}", stock=1, threshold=5)
        self.assertEqual(check_low_stock(), 1)
        msgs = self.messages()
        self.assertEqual(len(msgs), 1)
        self.assertIn("8 items", msgs[0].title)
        # Names a few, counts the rest, rather than listing all eight.
        self.assertIn("and 5 more", msgs[0].body)

    def test_the_emptiest_item_is_named_first(self):
        self.a_product("Plenty", stock=5, threshold=5)
        self.a_product("Empty", stock=0, threshold=5)
        check_low_stock()
        body = self.messages()[0].body
        self.assertLess(body.index("Empty"), body.index("Plenty"))

    # ─── Whose products ───────────────────────────────────────────────────────

    def test_a_hidden_product_is_not_reported(self):
        self.a_product("Draft", stock=0, threshold=5, active=False)
        self.assertEqual(check_low_stock(), 0)

    def test_an_unapproved_shop_is_not_reported(self):
        other_owner = User.objects.create_user(
            email="pending@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        pending = Business.objects.create(
            owner=other_owner,
            name="Not Yet",
            slug="not-yet",
            legal_name="Not Yet Ltd",
            registration_number="RC5550002",
            status=BusinessStatus.DRAFT,
        )
        Product.objects.create(
            business=pending, name="Rice", price=Decimal("1000"), stock=0, is_active=True
        )
        self.assertEqual(check_low_stock(), 0)

    def test_each_shop_gets_its_own_message(self):
        second_owner = User.objects.create_user(
            email="second@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        second = Business.objects.create(
            owner=second_owner,
            name="Other Shop",
            slug="other-shop-low",
            legal_name="Other Shop Ltd",
            registration_number="RC5550003",
            status=BusinessStatus.APPROVED,
        )
        self.a_product("Mine", stock=1, threshold=5)
        Product.objects.create(
            business=second, name="Theirs", price=Decimal("1000"), stock=1, is_active=True
        )

        self.assertEqual(check_low_stock(), 2)
        mine = self.messages()
        theirs = list(Notification.objects.filter(user=second_owner))
        self.assertEqual(len(mine), 1)
        self.assertEqual(len(theirs), 1)
        self.assertIn("Mine", mine[0].title)
        self.assertIn("Theirs", theirs[0].title)
        # No leaking between shops.
        self.assertNotIn("Theirs", mine[0].body)

    # ─── It runs from the scheduler ───────────────────────────────────────────

    def test_the_five_minute_task_calls_it(self):
        import tasks

        self.a_product("Rice", stock=1, threshold=5)
        tasks.warn_shops_about_low_stock()
        self.assertEqual(len(self.messages()), 1)
