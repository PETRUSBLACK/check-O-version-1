"""
The inbox, tested the way the app uses it.

Written on 2026-10-10, the day Petrus approved Shop O and said: "I did not
receive a notification saying the shop is open." He was right. Both messages
were in the database, unread, and would have stayed unread forever, because
nothing in the mobile app had ever mentioned notifications — no screen, no
service file, no bell.

The backend half had tests. On 2 October the low-stock warning got twelve of
them, about how restrained it was: that it fires once and not on every sale,
that it respects the threshold, that it does not nag. Twelve tests about the
manners of a message that had nowhere to arrive.

So these go through the API, with requests, the way a phone does — including the
two that matter most, which are that one person's inbox never shows or accepts a
mark on another person's messages.
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.notifications.services.notification_service import notify
from apps.users.models import User, UserRole


class InboxApiTest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.me = User.objects.create_user(
            email="owner@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.someone_else = User.objects.create_user(
            email="other@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.api.force_authenticate(self.me)

    def a_message(self, user=None, title="Shop O is open on Check-O", **kw):
        return Notification.objects.create(user=user or self.me, title=title, **kw)

    def rows(self, response):
        data = response.data
        return data.get("results", data) if isinstance(data, dict) else data

    # ─── Reading ──────────────────────────────────────────────────────────────

    def test_an_empty_inbox_is_an_empty_list_not_an_error(self):
        res = self.api.get("/api/notifications/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.rows(res), [])

    def test_my_notifications_come_back_newest_first(self):
        self.a_message(title="Older")
        self.a_message(title="Newer")
        titles = [n["title"] for n in self.rows(self.api.get("/api/notifications/"))]
        self.assertEqual(titles[:2], ["Newer", "Older"])

    def test_i_cannot_see_someone_elses_notifications(self):
        self.a_message(user=self.someone_else, title="Not for me")
        titles = [n["title"] for n in self.rows(self.api.get("/api/notifications/"))]
        self.assertNotIn("Not for me", titles)

    def test_i_cannot_fetch_someone_elses_notification_by_id(self):
        theirs = self.a_message(user=self.someone_else)
        res = self.api.get(f"/api/notifications/{theirs.pk}/")
        self.assertEqual(res.status_code, 404)

    def test_signing_out_means_no_inbox(self):
        self.api.force_authenticate(None)
        self.assertIn(self.api.get("/api/notifications/").status_code, (401, 403))

    # ─── The badge ────────────────────────────────────────────────────────────

    def test_unread_count_starts_at_zero(self):
        res = self.api.get("/api/notifications/unread-count/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["unread"], 0)

    def test_unread_count_counts_only_unread(self):
        self.a_message(title="Unread one")
        self.a_message(title="Unread two")
        self.a_message(title="Already seen", read_at=timezone.now())
        self.assertEqual(self.api.get("/api/notifications/unread-count/").data["unread"], 2)

    def test_unread_count_ignores_other_peoples_messages(self):
        self.a_message(user=self.someone_else, title="Theirs")
        self.assertEqual(self.api.get("/api/notifications/unread-count/").data["unread"], 0)

    # ─── Marking read ─────────────────────────────────────────────────────────

    def test_marking_one_read_sets_the_timestamp(self):
        mine = self.a_message()
        res = self.api.post(f"/api/notifications/{mine.pk}/read/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data["is_read"])
        mine.refresh_from_db()
        self.assertIsNotNone(mine.read_at)

    def test_marking_read_twice_does_not_move_the_timestamp(self):
        mine = self.a_message()
        self.api.post(f"/api/notifications/{mine.pk}/read/")
        mine.refresh_from_db()
        first = mine.read_at
        self.api.post(f"/api/notifications/{mine.pk}/read/")
        mine.refresh_from_db()
        self.assertEqual(mine.read_at, first)

    def test_i_cannot_mark_someone_elses_notification_read(self):
        theirs = self.a_message(user=self.someone_else)
        res = self.api.post(f"/api/notifications/{theirs.pk}/read/")
        self.assertEqual(res.status_code, 404)
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)

    def test_mark_all_read_clears_the_badge(self):
        self.a_message(title="One")
        self.a_message(title="Two")
        res = self.api.post("/api/notifications/read-all/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["marked"], 2)
        self.assertEqual(self.api.get("/api/notifications/unread-count/").data["unread"], 0)

    def test_mark_all_read_leaves_other_people_alone(self):
        self.a_message(user=self.someone_else, title="Theirs")
        self.api.post("/api/notifications/read-all/")
        self.assertIsNone(Notification.objects.get(title="Theirs").read_at)

    def test_the_words_cannot_be_edited(self):
        mine = self.a_message(title="Shop O is open on Check-O")
        self.api.patch(
            f"/api/notifications/{mine.pk}/", {"title": "Something else"}, format="json"
        )
        mine.refresh_from_db()
        self.assertEqual(mine.title, "Shop O is open on Check-O")

    # ─── Being able to act on one ─────────────────────────────────────────────

    def test_a_notification_carries_what_it_is_about(self):
        """
        The reason the inbox can do more than display words. Every `notify()`
        caller was already passing these ids; until today the row dropped them,
        so "Order Update: Shipped" had no way to open the order it meant.
        """
        notify(
            user=self.me,
            title="Order Update: Shipped",
            body="Your order is on its way!",
            event_type="order.status_changed",
            payload={"order_id": "11111111-1111-1111-1111-111111111111"},
        )
        row = self.rows(self.api.get("/api/notifications/"))[0]
        self.assertEqual(row["event_type"], "order.status_changed")
        self.assertEqual(row["payload"]["order_id"], "11111111-1111-1111-1111-111111111111")

    def test_a_notification_with_nothing_attached_still_works(self):
        """A plain message must not break the screen that renders the rich ones."""
        notify(user=self.me, title="Welcome to Check-O")
        row = self.rows(self.api.get("/api/notifications/"))[0]
        self.assertEqual(row["event_type"], "notification.new")
        self.assertEqual(row["payload"], {})
        self.assertFalse(row["is_read"])
