"""
Product photos: upload, cover selection, and who is allowed to touch them.

These tests exist because photo upload failed *silently*. A vendor uploaded a
photo from the app, got HTTP 201, and the photo never appeared anywhere. Three
separate causes, all invisible:

  1. MEDIA_URL had no leading slash, so a photo's URL came back relative and
     build_absolute_uri() turned it into /api/products/media/... — a 404.
  2. Nothing served MEDIA_ROOT at all in development.
  3. Photos must be sent as multipart (it's a file). DRF treats multipart as HTML
     form input, where an omitted BooleanField becomes False rather than the model
     default — so `is_active` was stamped False and the photo was hidden.

The third is the dangerous one: nothing errors, nothing logs, the photo is simply
never shown. `test_uploading_without_mentioning_is_active_still_shows_the_photo`
is the test that fails if it ever comes back.
"""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.products.models import Product, ProductImage
from apps.users.models import User, UserRole

# A real 1x1 PNG — ImageField runs it through Pillow, so it can't be junk bytes.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def a_photo(name="photo.png"):
    return SimpleUploadedFile(name, PNG, content_type="image/png")


class ProductPhotoTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email="shopowner@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.shop = Business.objects.create(
            owner=self.owner,
            name="Corner Shop",
            slug="corner-shop",
            legal_name="Corner Shop Ltd",
            registration_number="RC1111111",
            status=BusinessStatus.APPROVED,
        )
        self.product = Product.objects.create(
            business=self.shop, name="Rice", price=Decimal("10000.00"), stock=10, is_active=True
        )
        self.client.force_authenticate(self.owner)

    def upload(self, **extra):
        payload = {"product": str(self.product.id), "image": a_photo()}
        payload.update(extra)
        return self.client.post("/api/product-images/", payload, format="multipart")

    def cover_of(self, product_id=None):
        res = self.client.get(f"/api/products/{product_id or self.product.id}/")
        return res.data.get("cover_image")

    # ─── The silent failure ───────────────────────────────────────────────────

    def test_uploading_without_mentioning_is_active_still_shows_the_photo(self):
        """
        The app sends a file and a product id. It does not send is_active, and it
        should not have to. If this fails, photos are being uploaded and hidden.
        """
        res = self.upload()
        self.assertEqual(res.status_code, 201, res.data)

        image = ProductImage.objects.get(product=self.product)
        self.assertTrue(image.is_active, "the photo was saved hidden")
        self.assertIsNotNone(self.cover_of(), "the product has no cover photo")

    def test_the_photo_url_is_absolute_and_under_media(self):
        self.upload()
        cover = self.cover_of()
        self.assertIn("/media/", cover)
        # The bug produced .../api/products/<id>/media/... — guard the whole shape.
        self.assertNotIn("/api/", cover)
        self.assertTrue(cover.startswith("http"), cover)

    def test_the_file_is_on_disk_where_the_url_says_it_is(self):
        """
        Not a test that the URL *serves* — Django forces DEBUG=False in tests and
        `static()` deliberately serves nothing then, so a request here would 404
        however correct the wiring is. That half is verified against a real running
        server instead (see docs/DEV_LOG.md). What this pins down is that the file
        was genuinely written, and at the path the URL points to.
        """
        self.upload()
        path = self.cover_of().split("testserver", 1)[1]
        self.assertTrue(path.startswith(settings.MEDIA_URL), f"{path} is not under MEDIA_URL")

        on_disk = Path(settings.MEDIA_ROOT) / path[len(settings.MEDIA_URL):]
        self.assertTrue(on_disk.is_file(), f"nothing saved at {on_disk}")
        self.assertEqual(on_disk.read_bytes()[:8], PNG[:8], "the saved file is not the PNG")

    # ─── Cover selection ──────────────────────────────────────────────────────

    def test_first_photo_becomes_the_cover_on_its_own(self):
        self.upload()
        self.assertTrue(ProductImage.objects.get(product=self.product).is_cover)

    def test_marking_a_new_cover_demotes_the_old_one(self):
        self.upload()
        first = ProductImage.objects.get(product=self.product)

        res = self.upload(is_cover=True)
        self.assertEqual(res.status_code, 201, res.data)
        second = ProductImage.objects.get(pk=res.data["id"])

        first.refresh_from_db()
        self.assertFalse(first.is_cover, "two photos are both the cover")
        self.assertTrue(second.is_cover)
        self.assertEqual(
            ProductImage.objects.filter(product=self.product, is_cover=True).count(), 1
        )

    def test_a_hidden_photo_is_not_used_as_the_cover(self):
        self.upload()
        image = ProductImage.objects.get(product=self.product)
        res = self.client.patch(
            f"/api/product-images/{image.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIsNone(self.cover_of(), "a hidden photo is still being shown")

    # ─── Whose product is it ──────────────────────────────────────────────────

    def test_another_vendor_cannot_add_a_photo_to_your_product(self):
        intruder = User.objects.create_user(
            email="intruder@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        Business.objects.create(
            owner=intruder,
            name="Other Shop",
            slug="other-shop",
            legal_name="Other Shop Ltd",
            registration_number="RC2222222",
            status=BusinessStatus.APPROVED,
        )
        self.client.force_authenticate(intruder)
        res = self.upload()
        self.assertEqual(res.status_code, 403, res.data)
        self.assertFalse(ProductImage.objects.filter(product=self.product).exists())

    def test_a_shopper_cannot_add_a_photo(self):
        shopper = User.objects.create_user(
            email="shopper@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.client.force_authenticate(shopper)
        self.assertEqual(self.upload().status_code, 403)

    def test_another_vendor_cannot_delete_your_photo(self):
        self.upload()
        image = ProductImage.objects.get(product=self.product)

        intruder = User.objects.create_user(
            email="intruder2@example.com", password="testpass12345", role=UserRole.VENDOR
        )
        self.client.force_authenticate(intruder)
        res = self.client.delete(f"/api/product-images/{image.id}/")
        self.assertEqual(res.status_code, 403)
        self.assertTrue(ProductImage.objects.filter(pk=image.pk).exists())

    def test_the_owner_can_delete_their_photo(self):
        self.upload()
        image = ProductImage.objects.get(product=self.product)
        res = self.client.delete(f"/api/product-images/{image.id}/")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(ProductImage.objects.filter(pk=image.pk).exists())

    # ─── Shoppers see photos, not the shop's private numbers ──────────────────

    def test_a_shopper_sees_the_photo_but_not_the_cost_price(self):
        self.upload()
        shopper = User.objects.create_user(
            email="buyer@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.client.force_authenticate(shopper)
        body = self.client.get(f"/api/products/{self.product.id}/").data
        self.assertIsNotNone(body.get("cover_image"))
        self.assertNotIn("cost_price", body)
