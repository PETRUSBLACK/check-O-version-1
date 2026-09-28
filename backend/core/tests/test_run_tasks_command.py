"""
The background task runner.

The job that matters here cancels unpaid orders once their 30-minute window has
passed. It is the only thing that does, so these tests cover the two ways it gets
called and the mistake that is easy to make in each:

  --scheduled is stateless and assumes a 5-minute cron. Its "first 5 minutes of
  the hour" window is only correct at that cadence.

  --loop must therefore NOT use that window: at 60-second ticks it would run the
  hourly tasks five times every hour. It tracks last-run instead.
"""

from datetime import timedelta
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from core.management.commands.run_tasks import LAGOS


def at(hour: int, minute: int):
    """A fixed 'now' in Lagos time, as timezone.now() would return it."""
    return timezone.now().astimezone(LAGOS).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


class ScheduledModeTest(TestCase):
    """Stateless cron mode: what runs depends only on the clock."""

    def run_at(self, hour, minute):
        with patch("core.management.commands.run_tasks.timezone.now", return_value=at(hour, minute)):
            with patch("tasks.run_all_frequent_tasks") as frequent, patch(
                "tasks.run_all_hourly_tasks"
            ) as hourly, patch("tasks.run_all_daily_tasks") as daily:
                call_command("run_tasks", "--scheduled")
        return frequent.called, hourly.called, daily.called

    def test_frequent_tasks_run_every_time(self):
        """This is the one that cancels unpaid orders. It must never be skipped."""
        for hour, minute in [(0, 0), (3, 17), (13, 42), (23, 59)]:
            frequent, _, _ = self.run_at(hour, minute)
            self.assertTrue(frequent, f"frequent tasks skipped at {hour}:{minute:02d}")

    def test_hourly_tasks_run_at_the_top_of_the_hour_only(self):
        _, hourly, _ = self.run_at(14, 2)
        self.assertTrue(hourly)
        _, hourly, _ = self.run_at(14, 37)
        self.assertFalse(hourly)

    def test_daily_tasks_run_just_after_midnight_lagos(self):
        _, _, daily = self.run_at(0, 3)
        self.assertTrue(daily)
        _, _, daily = self.run_at(12, 3)
        self.assertFalse(daily, "daily tasks ran at midday")

    def test_nothing_selected_does_nothing_rather_than_guessing(self):
        with patch("tasks.run_all_frequent_tasks") as frequent:
            call_command("run_tasks")
        self.assertFalse(frequent.called)


class LoopModeTest(TestCase):
    """
    Loop mode. Each test lets the loop run a fixed number of rounds and then stops
    it, by having the sleep raise once it has seen enough.
    """

    def run_rounds(self, rounds: int, every: int = 300):
        calls = {"frequent": 0, "hourly": 0, "daily": 0}

        def stop_after(_seconds):
            if calls["frequent"] >= rounds:
                raise KeyboardInterrupt

        with patch("tasks.run_all_frequent_tasks", side_effect=lambda: calls.__setitem__("frequent", calls["frequent"] + 1)), \
             patch("tasks.run_all_hourly_tasks", side_effect=lambda: calls.__setitem__("hourly", calls["hourly"] + 1)), \
             patch("tasks.run_all_daily_tasks", side_effect=lambda: calls.__setitem__("daily", calls["daily"] + 1)), \
             patch("core.management.commands.run_tasks.time.sleep", side_effect=stop_after):
            try:
                call_command("run_tasks", "--loop", f"--every={every}")
            except KeyboardInterrupt:
                pass
        return calls

    def test_the_loop_keeps_going_round(self):
        calls = self.run_rounds(3)
        self.assertGreaterEqual(calls["frequent"], 3)

    def test_hourly_tasks_do_not_fire_every_round(self):
        """
        The bug this guards: with the stateless minute-window, a 60-second loop ran
        the hourly tasks on every round inside the first five minutes of the hour.
        """
        calls = self.run_rounds(5, every=60)
        self.assertGreaterEqual(calls["frequent"], 5)
        self.assertEqual(calls["hourly"], 1, "hourly tasks ran more than once")
        self.assertEqual(calls["daily"], 1, "daily tasks ran more than once")

    def test_one_failing_round_does_not_end_the_loop(self):
        """A database hiccup at 2am must not silently stop stock ever being released."""
        seen = {"n": 0}

        def sometimes_explode():
            seen["n"] += 1
            if seen["n"] == 2:
                raise RuntimeError("database went away")

        def stop_after(_seconds):
            if seen["n"] >= 4:
                raise KeyboardInterrupt

        with patch("tasks.run_all_frequent_tasks", side_effect=sometimes_explode), \
             patch("tasks.run_all_hourly_tasks"), patch("tasks.run_all_daily_tasks"), \
             patch("core.management.commands.run_tasks.time.sleep", side_effect=stop_after):
            try:
                call_command("run_tasks", "--loop", "--every=60")
            except KeyboardInterrupt:
                pass

        self.assertGreaterEqual(seen["n"], 4, "the loop stopped after one failure")

    def test_a_silly_interval_is_refused(self):
        with self.assertRaises(CommandError):
            call_command("run_tasks", "--loop", "--every=1")


class LoopActuallyCancelsTest(TestCase):
    """
    Not a mock in sight: a real unpaid order, past its window, cancelled by one
    round of the loop, with its stock returned.
    """

    def test_an_expired_unpaid_order_is_cancelled_and_stock_comes_back(self):
        from decimal import Decimal

        from apps.businesses.choices import BusinessStatus
        from apps.businesses.models import Business
        from apps.cart.services.cart_service import add_to_cart, checkout_cart
        from apps.orders.models import OrderStatus, StockReservation
        from apps.products.models import Product
        from apps.users.models import User, UserRole

        owner = User.objects.create_user(
            email="cronshop@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        shop = Business.objects.create(
            owner=owner,
            name="Cron Shop",
            slug="cron-shop",
            legal_name="Cron Shop Ltd",
            registration_number="RC7777777",
            status=BusinessStatus.APPROVED,
        )
        product = Product.objects.create(
            business=shop, name="Beans", price=Decimal("5000.00"), stock=10, is_active=True
        )
        customer = User.objects.create_user(
            email="croncustomer@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )

        add_to_cart(customer=customer, product_id=product.id, quantity=4)
        group = checkout_cart(customer=customer)
        order = group.orders.get()
        self.assertEqual(order.status, OrderStatus.PENDING_PAYMENT)

        # Wind the deadline back, as if the customer walked away 31 minutes ago.
        StockReservation.objects.filter(order=order).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )

        def stop_after(_seconds):
            raise KeyboardInterrupt

        with patch("core.management.commands.run_tasks.time.sleep", side_effect=stop_after):
            try:
                call_command("run_tasks", "--loop", "--every=60")
            except KeyboardInterrupt:
                pass

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED, "the unpaid order was not cancelled")
        self.assertEqual(order.cancellation_reason, "payment_timeout")

        product.refresh_from_db()
        self.assertEqual(product.available_stock, 10, "the stock did not come back")
