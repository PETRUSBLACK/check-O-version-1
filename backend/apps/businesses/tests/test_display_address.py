"""
Which address a customer sees on a shop page.

There are two addresses in the database and vendors rarely fill both:
`Business.address` is typed on the business form and often left blank, while the
location row's address is the one carrying the GPS used for distance.

The shop page used to show `Business.address` alone, so a shop that had only
filled in its location showed no address at all. `display_address` resolves it:
prefer the location, fall back to the business field, never return null.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.businesses.choices import BusinessStatus
from decimal import Decimal

from apps.businesses.models import Business, BusinessLocation
from apps.users.models import User, UserRole


class DisplayAddressTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email="addr@example.com", password="testpass12345", role=UserRole.VENDOR
        )

    def a_shop(self, slug, business_address=""):
        return Business.objects.create(
            owner=self.owner,
            name=f"Shop {slug}",
            slug=slug,
            legal_name=f"Shop {slug} Ltd",
            registration_number=f"RC{abs(hash(slug)) % 9000000 + 1000000}",
            status=BusinessStatus.APPROVED,
            address=business_address,
        )

    def a_location(self, shop, address, city="", state=""):
        """A location row always carries coordinates — that is what it is for."""
        return BusinessLocation.objects.create(
            business=shop,
            address=address,
            city=city,
            state=state,
            latitude=Decimal("6.2003000"),
            longitude=Decimal("6.7331000"),
        )

    def shown_for(self, shop) -> str:
        res = self.client.get(f"/api/businesses/{shop.id}/")
        self.assertEqual(res.status_code, 200, res.data)
        return res.data["display_address"]

    # ─── The case that was broken ─────────────────────────────────────────────

    def test_location_only_still_shows_an_address(self):
        """The common real case: the vendor set a location and left the form blank."""
        shop = self.a_shop("loc-only", business_address="")
        self.a_location(shop, "42 Nnebisi Road", "Asaba", "Delta")
        shown = self.shown_for(shop)
        self.assertIn("42 Nnebisi Road", shown)
        self.assertIn("Asaba", shown)

    # ─── The other arrangements ───────────────────────────────────────────────

    def test_business_address_only_is_used_when_there_is_no_location(self):
        shop = self.a_shop("biz-only", business_address="7 Ibusa Road, Asaba")
        self.assertEqual(self.shown_for(shop), "7 Ibusa Road, Asaba")

    def test_the_location_wins_when_both_are_filled(self):
        """The location is the one tied to the GPS, so it is the more trustworthy."""
        shop = self.a_shop("both", business_address="old address nobody updated")
        self.a_location(shop, "5 Okpanam Road", "Asaba", "Delta")
        shown = self.shown_for(shop)
        self.assertIn("5 Okpanam Road", shown)
        self.assertNotIn("old address", shown)

    def test_neither_filled_gives_an_empty_string_not_null(self):
        """The app prints this straight onto the screen; None would read as "null"."""
        shop = self.a_shop("neither", business_address="")
        self.assertEqual(self.shown_for(shop), "")

    def test_the_city_is_not_repeated_when_the_street_line_already_says_it(self):
        shop = self.a_shop("no-dupe")
        self.a_location(shop, "18 DLA Road, Asaba", "Asaba", "Delta")
        shown = self.shown_for(shop)
        self.assertEqual(shown.lower().count("asaba"), 1, shown)

    def test_whitespace_only_address_counts_as_empty(self):
        shop = self.a_shop("blank", business_address="   ")
        self.a_location(shop, "   ", "Asaba")
        # The location's address is blank, so it falls through to the business
        # field, which is also blank.
        self.assertEqual(self.shown_for(shop), "")

    # ─── It must not cost a query per shop ────────────────────────────────────

    def test_a_shop_page_does_not_add_a_query_for_the_address(self):
        shop = self.a_shop("queries")
        self.a_location(shop, "1 Test Road", "Asaba")
        self.client.force_authenticate(self.owner)
        with self.assertNumQueries(3):
            # user + business (with location joined) + ratings prefetch.
            self.client.get(f"/api/businesses/{shop.id}/")
