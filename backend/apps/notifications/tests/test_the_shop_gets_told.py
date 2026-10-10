"""
The shop has to be told too.

Found on 2026-10-10 while debugging the new inbox. Every notification helper in
Check-O was addressed to `order.customer` — placed, paid, status changed,
shipment moved, pickup due. Not one reached the person who has to pack the bag.

Petrus's reaction when I mentioned it was the right one: "why should a shop
owner not receive notifications?" There is no reason. It was never a decision,
it was an omission, and it survived because the shop side of Check-O was built
outwards from the shopper side and because until that morning nothing in the
app could display a notification at all — so there was nothing to miss.

These tests exist in the shape of the gap: for every message, who gets it.
"""

from decimal import Decimal

from django.test import TestCase

from apps.businesses.choices import BusinessCategory, BusinessStatus
from apps.businesses.models import Business
from apps.notifications.models import Notification
from apps.orders.models import (
    CancellationReason,
    CancelledBy,
    Order,
    OrderItem,
    OrderStatus,
)
from apps.orders.services.order_service import transition_order_status
from apps.products.models import Product
from apps.users.models import User, UserRole


class TheShopGetsToldTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="grace@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.shopper = User.objects.create_user(
            email="buyer@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.shop = Business.objects.create(
            owner=self.owner,
            name="Grace Provisions",
            slug="grace-provisions",
            category=BusinessCategory.SUPERMARKET,
            status=BusinessStatus.APPROVED,
        )
        self.product = Product.objects.create(
            business=self.shop, name="Rice 50kg", price=Decimal("68000.00"), stock=10
        )

    def an_order(self, *, status=OrderStatus.PENDING_PAYMENT.value, quantity=2):
        order = Order.objects.create(
            customer=self.shopper,
            business=self.shop,
            status=status,
            recipient_name="Chidi Okeke",
            total=Decimal("68000.00") * quantity,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=quantity,
            unit_price=self.product.price,
        )
        return order

    def messages_for(self, user, event_type=None):
        rows = Notification.objects.filter(user=user)
        return list(rows.filter(event_type=event_type) if event_type else rows)

    # ─── A paid order ─────────────────────────────────────────────────────────

    def test_the_shop_is_told_when_an_order_is_paid(self):
        """The one that was missing. Money arrives and nobody tells the shop."""
        order = self.an_order()
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)

        told = self.messages_for(self.owner, "vendor.new_order")
        self.assertEqual(len(told), 1, "the shop owner was not told about a paid order")

    def test_that_message_says_what_the_shop_needs_to_know(self):
        order = self.an_order(quantity=3)
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)

        message = self.messages_for(self.owner, "vendor.new_order")[0]
        self.assertIn("204,000", message.title)  # the money, in the title
        self.assertIn("3 items", message.body)
        self.assertIn("Chidi Okeke", message.body)

    def test_it_can_be_opened(self):
        """A message about an order that cannot open the order is half a message."""
        order = self.an_order()
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)

        message = self.messages_for(self.owner, "vendor.new_order")[0]
        self.assertEqual(message.payload["order_id"], str(order.pk))

    def test_the_customer_still_gets_their_own_message(self):
        """Telling the shop must not have taken anything away from the shopper."""
        order = self.an_order()
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)
        self.assertTrue(self.messages_for(self.shopper))

    def test_an_unpaid_order_does_not_disturb_the_shop(self):
        """
        A pending order is a 30-minute hold that may simply lapse. Sending a
        trader to pack something that might evaporate teaches her to ignore
        Check-O, which costs more than the message is worth.
        """
        self.an_order()
        self.assertEqual(self.messages_for(self.owner, "vendor.new_order"), [])

    def test_the_shop_is_not_told_twice_for_one_payment(self):
        order = self.an_order()
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)
        # Moving on through the shop's own workflow must not re-announce it.
        transition_order_status(order_id=order.pk, to_status=OrderStatus.PROCESSING.value)
        self.assertEqual(len(self.messages_for(self.owner, "vendor.new_order")), 1)

    # ─── A cancelled order ────────────────────────────────────────────────────

    def test_the_shop_is_told_when_the_customer_cancels(self):
        from apps.orders.services.order_service import _apply_cancellation

        order = self.an_order(status=OrderStatus.PAID.value)
        Notification.objects.all().delete()
        _apply_cancellation(
            order=order,
            by=CancelledBy.CUSTOMER,
            user=self.shopper,
            reason=CancellationReason.OTHER,
        )
        told = self.messages_for(self.owner, "vendor.order_cancelled")
        self.assertEqual(len(told), 1)
        self.assertIn("back on your shelf", told[0].body)

    def test_the_shop_is_not_told_about_its_own_cancellation(self):
        """A vendor does not need a message announcing what she just did."""
        from apps.orders.services.order_service import _apply_cancellation

        order = self.an_order(status=OrderStatus.PAID.value)
        Notification.objects.all().delete()
        _apply_cancellation(
            order=order,
            by=CancelledBy.VENDOR,
            user=self.owner,
            reason=CancellationReason.OUT_OF_STOCK,
        )
        self.assertEqual(self.messages_for(self.owner, "vendor.order_cancelled"), [])

    # ─── Nothing breaks without a shop ────────────────────────────────────────

    def test_an_order_with_no_shop_does_not_raise(self):
        """
        `Order.business` is nullable. A message that cannot be addressed should
        be skipped quietly — it must never stop an order being paid for.
        """
        order = self.an_order()
        order.business = None
        order.save(update_fields=["business"])

        transition_order_status(order_id=order.pk, to_status=OrderStatus.PAID.value)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PAID.value)
