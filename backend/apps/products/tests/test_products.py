from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessStatus
from apps.products.models import Product
from apps.users.models import User, UserRole


def make_user(email, role=UserRole.CUSTOMER, password="testpass12345"):
    return User.objects.create_user(email=email, password=password, role=role)


def make_vendor(email="vendor@example.com"):
    return make_user(email, role=UserRole.VENDOR)


def make_business(owner, status=BusinessStatus.APPROVED, slug="test-shop"):
    return Business.objects.create(
        owner=owner,
        name="Test Shop",
        slug=slug,
        legal_name="Test Shop Ltd",
        registration_number="RC1234567",
        status=status,
    )


def make_product(business, name="Widget", price="10.00", stock=50, is_active=True):
    return Product.objects.create(
        business=business,
        name=name,
        price=price,
        stock=stock,
        is_active=is_active,
    )


class ProductModelTest(TestCase):

    def test_product_has_uuid_pk(self):
        vendor = make_vendor()
        business = make_business(vendor)
        product = make_product(business)
        self.assertIsNotNone(product.pk)
        self.assertEqual(len(str(product.pk)), 36)

    def test_product_str(self):
        vendor = make_vendor()
        business = make_business(vendor)
        product = make_product(business, name="Test Widget")
        self.assertEqual(str(product), "Test Widget")


class ProductCreateTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_vendor_can_create_product_for_approved_business(self):
        vendor = make_vendor()
        business = make_business(vendor, status=BusinessStatus.APPROVED)
        self.client.force_authenticate(vendor)
        res = self.client.post("/api/products/", {
            "business": str(business.pk),
            "name": "New Product",
            "price": "25.00",
            "stock": 10,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.filter(business=business).count(), 1)

    def test_vendor_cannot_create_product_for_unapproved_business(self):
        vendor = make_vendor()
        business = make_business(vendor, status=BusinessStatus.PENDING)
        self.client.force_authenticate(vendor)
        res = self.client.post("/api/products/", {
            "business": str(business.pk),
            "name": "New Product",
            "price": "25.00",
            "stock": 10,
        }, format="json")
        self.assertIn(res.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])

    def test_vendor_cannot_create_product_for_another_vendors_business(self):
        vendor1 = make_vendor("v1@example.com")
        vendor2 = make_vendor("v2@example.com")
        business = make_business(vendor2, slug="v2-shop")
        self.client.force_authenticate(vendor1)
        res = self.client.post("/api/products/", {
            "business": str(business.pk),
            "name": "Sneaky Product",
            "price": "10.00",
            "stock": 5,
        }, format="json")
        self.assertIn(res.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])

    def test_customer_cannot_create_product(self):
        vendor = make_vendor()
        business = make_business(vendor)
        customer = make_user("cust@example.com", role=UserRole.CUSTOMER)
        self.client.force_authenticate(customer)
        res = self.client.post("/api/products/", {
            "business": str(business.pk),
            "name": "Product",
            "price": "10.00",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_product(self):
        res = self.client.post("/api/products/", {"name": "X"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class ProductReadTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_public_sees_only_active_products_from_approved_businesses(self):
        vendor = make_vendor()
        approved_biz = make_business(vendor, status=BusinessStatus.APPROVED, slug="approved")
        pending_biz = make_business(vendor, status=BusinessStatus.PENDING, slug="pending")
        make_product(approved_biz, name="Active Product", is_active=True)
        make_product(approved_biz, name="Inactive Product", is_active=False)
        make_product(pending_biz, name="Pending Biz Product", is_active=True)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in res.data["results"]]
        self.assertIn("Active Product", names)
        self.assertNotIn("Inactive Product", names)
        self.assertNotIn("Pending Biz Product", names)

    def test_vendor_sees_own_products_including_inactive(self):
        vendor = make_vendor()
        business = make_business(vendor)
        make_product(business, name="Active", is_active=True)
        make_product(business, name="Inactive", is_active=False)
        self.client.force_authenticate(vendor)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in res.data["results"]]
        self.assertIn("Active", names)
        self.assertIn("Inactive", names)

    def test_vendor_does_not_see_other_vendors_products(self):
        vendor1 = make_vendor("v1@example.com")
        vendor2 = make_vendor("v2@example.com")
        biz1 = make_business(vendor1, slug="biz1")
        biz2 = make_business(vendor2, slug="biz2")
        make_product(biz1, name="V1 Product")
        make_product(biz2, name="V2 Product")
        self.client.force_authenticate(vendor1)
        res = self.client.get("/api/products/")
        names = [p["name"] for p in res.data["results"]]
        self.assertIn("V1 Product", names)
        self.assertNotIn("V2 Product", names)


class ProductUpdateDeleteTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_vendor_can_update_own_product(self):
        vendor = make_vendor()
        business = make_business(vendor)
        product = make_product(business)
        self.client.force_authenticate(vendor)
        res = self.client.patch(
            f"/api/products/{product.pk}/",
            {"name": "Updated Widget"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertEqual(product.name, "Updated Widget")

    def test_vendor_cannot_update_another_vendors_product(self):
        vendor1 = make_vendor("v1@example.com")
        vendor2 = make_vendor("v2@example.com")
        biz2 = make_business(vendor2, slug="biz2")
        product = make_product(biz2)
        self.client.force_authenticate(vendor1)
        res = self.client.patch(
            f"/api/products/{product.pk}/",
            {"name": "Stolen"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_vendor_can_delete_own_product(self):
        vendor = make_vendor()
        business = make_business(vendor)
        product = make_product(business)
        self.client.force_authenticate(vendor)
        res = self.client.delete(f"/api/products/{product.pk}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_vendor_cannot_delete_another_vendors_product(self):
        vendor1 = make_vendor("v1@example.com")
        vendor2 = make_vendor("v2@example.com")
        biz2 = make_business(vendor2, slug="biz2")
        product = make_product(biz2)
        self.client.force_authenticate(vendor1)
        res = self.client.delete(f"/api/products/{product.pk}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
