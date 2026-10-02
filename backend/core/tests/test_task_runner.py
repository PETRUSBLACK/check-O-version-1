"""
The cron webhook that runs Check-O's background tasks in production.

This endpoint is load-bearing in a way that is easy to miss. Nothing else cancels
an unpaid order, so if it stops working, every abandoned payment holds a vendor's
stock until someone notices by hand. And because it is reachable from the open
internet, the token check is the only thing standing between a stranger and the
ability to drive the scheduler.

So: the door is shut by default, the token is checked properly, and a failure in
one tier of tasks does not stop the others.
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings

from core.task_runner import TOKEN_HEADER, run_due_tasks, tiers_due_now

LAGOS = dt_timezone(timedelta(hours=1))

URL = "/api/internal/run-tasks/"
TOKEN = "a-long-random-production-token"
# Django's test client turns X-Task-Token into this.
HEADER = {"HTTP_X_TASK_TOKEN": TOKEN}


class WhichTiersAreDueTest(TestCase):
    """
    The rule is stateless so a cron service needs to remember nothing. It is only
    correct at a 5-minute cadence, which is why run_tasks --loop does not use it.
    """

    def at(self, hour, minute):
        return datetime(2026, 10, 2, hour, minute, tzinfo=LAGOS)

    def test_the_frequent_tasks_run_every_single_time(self):
        for hour, minute in ((0, 0), (9, 17), (23, 55)):
            self.assertTrue(tiers_due_now(self.at(hour, minute))["frequent"])

    def test_the_hourly_tasks_run_once_at_the_top_of_the_hour(self):
        due_at = [m for m in range(0, 60, 5) if tiers_due_now(self.at(14, m))["hourly"]]
        self.assertEqual(due_at, [0], "exactly one 5-minute slot per hour")

    def test_the_daily_tasks_run_once_at_midnight_lagos_time(self):
        self.assertTrue(tiers_due_now(self.at(0, 0))["daily"])
        self.assertFalse(tiers_due_now(self.at(0, 10))["daily"])
        self.assertFalse(tiers_due_now(self.at(1, 0))["daily"])
        # Midnight UTC is 1am in Asaba, and is not the start of the day here.
        self.assertFalse(
            tiers_due_now(datetime(2026, 10, 2, 0, 0, tzinfo=dt_timezone.utc))["daily"]
        )

    def test_the_management_command_uses_the_same_rule(self):
        """
        Two copies of "is the hourly tier due" would drift, and the symptom would
        be tasks quietly running five times an hour.
        """
        import core.management.commands.run_tasks as command_module

        self.assertIs(command_module.tiers_due_now, tiers_due_now)


class TheDoorIsShutByDefaultTest(TestCase):
    @override_settings(TASK_RUNNER_TOKEN="")
    def test_with_no_token_configured_nobody_gets_in(self):
        """
        Every development machine has no token. The endpoint must not be an open
        way to drive the scheduler just because someone forgot to set one.
        """
        with patch("core.task_runner.run_due_tasks") as ran:
            res = self.client.post(URL)
        self.assertEqual(res.status_code, 503)
        ran.assert_not_called()

    @override_settings(TASK_RUNNER_TOKEN=TOKEN)
    def test_no_header_is_refused(self):
        with patch("core.task_runner.run_due_tasks") as ran:
            res = self.client.post(URL)
        self.assertEqual(res.status_code, 401)
        ran.assert_not_called()

    @override_settings(TASK_RUNNER_TOKEN=TOKEN)
    def test_a_wrong_token_is_refused(self):
        with patch("core.task_runner.run_due_tasks") as ran:
            res = self.client.post(URL, **{"HTTP_X_TASK_TOKEN": "nearly-the-right-token"})
        self.assertEqual(res.status_code, 401)
        ran.assert_not_called()

    @override_settings(TASK_RUNNER_TOKEN=TOKEN)
    def test_a_token_that_is_merely_a_prefix_is_refused(self):
        with patch("core.task_runner.run_due_tasks") as ran:
            res = self.client.post(URL, **{"HTTP_X_TASK_TOKEN": TOKEN[:-1]})
        self.assertEqual(res.status_code, 401)
        ran.assert_not_called()


@override_settings(TASK_RUNNER_TOKEN=TOKEN)
class TheRightTokenRunsThemTest(TestCase):
    def test_the_correct_token_runs_the_tasks_and_says_which(self):
        res = self.client.post(URL, **HEADER)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["status"], "ok")
        self.assertIn("frequent", res.json()["ran"])

    def test_a_get_works_too(self):
        """
        It mutates, so by the book it should be POST only — but several free cron
        services will only issue a GET, and a scheduler that cannot reach the
        endpoint is worse than an impure verb.
        """
        res = self.client.get(URL, **HEADER)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn("frequent", res.json()["ran"])

    def test_it_needs_no_login(self):
        """The caller is a cron service. It has no account and needs none."""
        res = self.client.post(URL, **HEADER)
        self.assertEqual(res.status_code, 200)

    def test_one_broken_tier_does_not_stop_the_others(self):
        """
        A failing daily subscription renewal must not stop unpaid orders being
        cancelled — that one is the difference between a shop's stock being free
        to sell and being held by a customer who walked away an hour ago.
        """
        midnight = datetime(2026, 10, 2, 0, 0, tzinfo=LAGOS)
        with patch("tasks.run_all_daily_tasks", side_effect=RuntimeError("database gone")):
            with patch("tasks.run_all_frequent_tasks") as frequent:
                outcome = run_due_tasks(midnight)

        frequent.assert_called_once()
        self.assertIn("frequent", outcome["ran"])
        self.assertIn("daily", outcome["failed"])
        self.assertIn("database gone", outcome["failed"]["daily"])

    def test_a_failure_is_reported_rather_than_a_500(self):
        """
        A cron service shows the status code and nothing else. A 500 says only
        "something broke"; a 200 carrying the failure says what.
        """
        with patch("tasks.run_all_frequent_tasks", side_effect=RuntimeError("boom")):
            res = self.client.post(URL, **HEADER)
        self.assertEqual(res.status_code, 200)
        self.assertIn("frequent", res.json()["failed"])


@override_settings(TASK_RUNNER_TOKEN=TOKEN)
class ItActuallyCancelsAnUnpaidOrderTest(TestCase):
    """
    The point of the whole thing, proved end to end rather than mocked: an order
    whose payment window has passed is cancelled by an HTTP request, and its stock
    goes back on the shelf.
    """

    def setUp(self):
        from apps.businesses.choices import BusinessStatus
        from apps.businesses.models import Business
        from apps.products.models import Product
        from apps.users.models import User, UserRole

        self.owner = User.objects.create_user(
            email="cronshop@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.shop = Business.objects.create(
            owner=self.owner,
            name="Cron Test Shop",
            slug="cron-test-shop",
            status=BusinessStatus.APPROVED,
        )
        self.product = Product.objects.create(
            business=self.shop,
            name="Bag of rice",
            price=Decimal("68000.00"),
            stock=10,
            is_active=True,
        )

    def test_an_expired_hold_is_released_by_a_request_to_the_endpoint(self):
        from django.utils import timezone

        from apps.orders.models import Order, OrderStatus
        from apps.orders.services.stock_service import reserve_stock
        from apps.users.models import User, UserRole

        customer = User.objects.create_user(
            email="walkedaway@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        order = Order.objects.create(
            customer=customer,
            status=OrderStatus.PENDING_PAYMENT,
            total=Decimal("68000.00"),
        )
        hold = reserve_stock(order=order, product=self.product, quantity=3)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7, "the hold should have taken the stock")

        # The 30-minute window lives on the reservation, not the order. Push it
        # into the past, the way a customer who closed the payment page and never
        # came back leaves it.
        hold.expires_at = timezone.now() - timedelta(minutes=5)
        hold.save(update_fields=["expires_at"])

        res = self.client.post(URL, **HEADER)
        self.assertEqual(res.status_code, 200, res.content)

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(self.product.stock, 10, "the stock should be back on the shelf")
