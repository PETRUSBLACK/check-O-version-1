"""
Pasting a location instead of typing coordinates.

A shop with no coordinates never appears in "Shops near you", so the admin must
make them easy to supply — and must not let a shop be saved without them.
"""

from django.test import TestCase

from apps.businesses.admin import BusinessLocationForm, parse_coordinates
from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.users.models import User, UserRole

ASABA = (6.2003, 6.7331)


class ParseCoordinatesTest(TestCase):
    def test_plain_pair(self):
        self.assertEqual(parse_coordinates("6.2003, 6.7331"), ASABA)

    def test_pair_without_a_space(self):
        self.assertEqual(parse_coordinates("6.2003,6.7331"), ASABA)

    def test_google_maps_url_with_at_sign(self):
        url = "https://www.google.com/maps/@6.2003,6.7331,17z"
        self.assertEqual(parse_coordinates(url), ASABA)

    def test_google_maps_place_url(self):
        """The long share link Google gives for a named place."""
        url = (
            "https://www.google.com/maps/place/Asaba/data=!3m1!4b1!4m6"
            "!3m5!1s0x1234!8m2!3d6.2003!4d6.7331"
        )
        self.assertEqual(parse_coordinates(url), ASABA)

    def test_google_maps_query_url(self):
        self.assertEqual(parse_coordinates("https://maps.google.com/?q=6.2003,6.7331"), ASABA)

    def test_negative_coordinates(self):
        self.assertEqual(parse_coordinates("-33.9249, 18.4241"), (-33.9249, 18.4241))

    def test_nothing_usable(self):
        self.assertIsNone(parse_coordinates(""))
        self.assertIsNone(parse_coordinates("Okpanam Road, Asaba"))

    def test_numbers_outside_the_world_are_refused(self):
        self.assertIsNone(parse_coordinates("500.1234, 6.7331"))


class BusinessLocationFormTest(TestCase):
    def setUp(self):
        owner = User.objects.create_user(
            email="owner@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.business = Business.objects.create(
            owner=owner,
            name="Mama Nkechi Stores",
            slug="mama-nkechi",
            legal_name="Mama Nkechi Stores Ltd",
            registration_number="RC1234567",
            status=BusinessStatus.APPROVED,
        )

    def form(self, **extra):
        data = {
            "business": str(self.business.id),
            "address": "12 Nnebisi Road",
            "city": "Asaba",
            "state": "Delta",
            "country": "Nigeria",
            "postal_code": "",
            "coordinates": "",
            "latitude": "",
            "longitude": "",
        }
        data.update(extra)
        return BusinessLocationForm(data=data)

    def test_pasted_link_fills_the_coordinates(self):
        form = self.form(coordinates="https://www.google.com/maps/@6.2003,6.7331,17z")
        self.assertTrue(form.is_valid(), form.errors)
        location = form.save()
        self.assertAlmostEqual(float(location.latitude), 6.2003)
        self.assertAlmostEqual(float(location.longitude), 6.7331)

    def test_typing_the_numbers_still_works(self):
        form = self.form(latitude="6.2003", longitude="6.7331")
        self.assertTrue(form.is_valid(), form.errors)

    def test_pasted_coordinates_win_over_typed_ones(self):
        form = self.form(coordinates="6.5000, 6.9000", latitude="1.0", longitude="2.0")
        self.assertTrue(form.is_valid(), form.errors)
        location = form.save()
        self.assertAlmostEqual(float(location.latitude), 6.5)

    def test_unusable_paste_is_explained(self):
        form = self.form(coordinates="near the roundabout")
        self.assertFalse(form.is_valid())
        self.assertIn("Couldn't find coordinates", " ".join(form.non_field_errors()))

    def test_a_shop_cannot_be_saved_with_no_location(self):
        form = self.form()
        self.assertFalse(form.is_valid())
        self.assertIn("won't show up in the app", " ".join(form.non_field_errors()))
