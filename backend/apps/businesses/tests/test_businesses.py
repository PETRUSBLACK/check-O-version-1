from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessStatus
from apps.users.models import User, UserRole


def make_user(email, role=UserRole.CUSTOMER, password="testpass12345"):
    return User.objects.create_user(email=email, password=password, role=role)


def make_vendor(email="vendor@example.com"):
    return make_user(email, role=UserRole.VENDOR)


def make_business(owner, name="Test Shop", slug="test-shop", status=BusinessStatus.DRAFT):
    return Business.objects.create(
        owner=owner,
        name=name,
        slug=slug,
        legal_name="Test Shop Ltd",
        registration_number="RC1234567",
        status=status,
    )


class BusinessModelTest(TestCase):

    def test_business_has_uuid_pk(self):
        vendor = make_vendor()
        business = make_business(vendor)
        self.assertIsNotNone(business.pk)
        self.assertEqual(len(str(business.pk)), 36)  # UUID format

    def test_business_str(self):
        vendor = make_vendor()
        business = make_business(vendor)
        self.assertEqual(str(business), "Test Shop")

    def test_default_status_is_draft(self):
        vendor = make_vendor()
        business = make_business(vendor)
        self.assertEqual(business.status, BusinessStatus.DRAFT)


class BusinessCreateTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_vendor_can_create_business(self):
        vendor = make_vendor()
        self.client.force_authenticate(vendor)
        res = self.client.post("/api/businesses/", {
            "name": "My Shop",
            "slug": "my-shop",
            "legal_name": "My Shop Ltd",
            "registration_number": "RC9876543",
            "address": "1 Lagos Street",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Business.objects.filter(owner=vendor).count(), 1)

    def test_customer_cannot_create_business(self):
        customer = make_user("cust@example.com", role=UserRole.CUSTOMER)
        self.client.force_authenticate(customer)
        res = self.client.post("/api/businesses/", {
            "name": "My Shop",
            "slug": "my-shop",
        }, format="json")
        self.assertIn(res.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])

    def test_unauthenticated_cannot_create_business(self):
        res = self.client.post("/api/businesses/", {"name": "X", "slug": "x"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_slug_rejected(self):
        vendor = make_vendor()
        make_business(vendor, slug="my-shop")
        self.client.force_authenticate(vendor)
        res = self.client.post("/api/businesses/", {
            "name": "Another Shop",
            "slug": "my-shop",
            "legal_name": "Another Ltd",
            "registration_number": "RC0000001",
        }, format="json")
        self.assertNotEqual(res.status_code, status.HTTP_201_CREATED)


class BusinessReadTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_public_can_list_approved_businesses(self):
        vendor = make_vendor()
        make_business(vendor, slug="draft-biz", status=BusinessStatus.DRAFT)
        make_business(vendor, name="Approved Biz", slug="approved-biz", status=BusinessStatus.APPROVED)
        res = self.client.get("/api/businesses/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = [b["name"] for b in res.data["results"]]
        self.assertIn("Approved Biz", names)
        self.assertNotIn("Test Shop", names)

    def test_vendor_sees_own_businesses_only(self):
        vendor1 = make_vendor("v1@example.com")
        vendor2 = make_vendor("v2@example.com")
        make_business(vendor1, slug="biz-1")
        make_business(vendor2, name="Biz 2", slug="biz-2")
        self.client.force_authenticate(vendor1)
        res = self.client.get("/api/businesses/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["name"], "Test Shop")

    def test_admin_sees_all_businesses(self):
        vendor = make_vendor()
        admin = make_user("admin@example.com", role=UserRole.ADMIN)
        admin.is_staff = True
        admin.save()
        make_business(vendor, slug="biz-a", status=BusinessStatus.DRAFT)
        make_business(vendor, name="Biz B", slug="biz-b", status=BusinessStatus.APPROVED)
        self.client.force_authenticate(admin)
        res = self.client.get("/api/businesses/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)


class BusinessWorkflowTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_vendor_can_submit_draft_for_review(self):
        vendor = make_vendor()
        business = make_business(vendor, status=BusinessStatus.DRAFT)
        self.client.force_authenticate(vendor)
        res = self.client.post(f"/api/businesses/{business.pk}/submit-for-review/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        business.refresh_from_db()
        self.assertEqual(business.status, BusinessStatus.PENDING)

    def test_admin_can_approve_pending_business(self):
        vendor = make_vendor()
        business = make_business(vendor, status=BusinessStatus.PENDING)
        admin = make_user("admin@example.com", role=UserRole.ADMIN)
        admin.is_staff = True
        admin.save()
        self.client.force_authenticate(admin)
        res = self.client.post(f"/api/businesses/{business.pk}/approve/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        business.refresh_from_db()
        self.assertEqual(business.status, BusinessStatus.APPROVED)

    def test_admin_can_reject_pending_business(self):
        vendor = make_vendor()
        business = make_business(vendor, status=BusinessStatus.PENDING)
        admin = make_user("admin@example.com", role=UserRole.ADMIN)
        admin.is_staff = True
        admin.save()
        self.client.force_authenticate(admin)
        res = self.client.post(
            f"/api/businesses/{business.pk}/reject/",
            {"reason": "Incomplete documents."},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        business.refresh_from_db()
        self.assertEqual(business.status, BusinessStatus.REJECTED)
        self.assertEqual(business.rejection_reason, "Incomplete documents.")

    def test_vendor_cannot_approve_business(self):
        vendor = make_vendor()
        business = make_business(vendor, status=BusinessStatus.PENDING)
        self.client.force_authenticate(vendor)
        res = self.client.post(f"/api/businesses/{business.pk}/approve/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_submit_already_pending_business(self):
        vendor = make_vendor()
        business = make_business(vendor, status=BusinessStatus.PENDING)
        self.client.force_authenticate(vendor)
        res = self.client.post(f"/api/businesses/{business.pk}/submit-for-review/")
        self.assertNotEqual(res.status_code, status.HTTP_200_OK)

    def test_vendor_can_edit_rejected_business(self):
        vendor = make_vendor()
        business = make_business(vendor, status=BusinessStatus.REJECTED)
        self.client.force_authenticate(vendor)
        res = self.client.patch(
            f"/api/businesses/{business.pk}/",
            {"address": "Updated Address"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_vendor_cannot_edit_approved_business(self):
        vendor = make_vendor()
        business = make_business(vendor, status=BusinessStatus.APPROVED)
        self.client.force_authenticate(vendor)
        res = self.client.patch(
            f"/api/businesses/{business.pk}/",
            {"address": "Sneaky update"},
            format="json",
        )
        self.assertIn(res.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])
