"""
A vendor may only touch their own shop's orders.

Being a vendor is not enough: every fulfilment endpoint has to check which shop
the order belongs to, or one shop could move another's orders around.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.cart.services.cart_service import add_to_cart, checkout_cart
from apps.orders.models import Order, OrderStatus
from apps.products.models import Product
from apps.users.models import User, UserRole


def make_shop(slug, *, delivers=False):
    owner = User.objects.create_user(
        email=f"{slug}@example.com", password="testpass12345", role=UserRole.VENDOR
    )
    shop = Business.objects.create(
        owner=owner,
        name=slug.title(),
        slug=slug,
        legal_name=slug.title() + " Ltd",
        registration_number="RC" + slug[:6].upper(),
        status=BusinessStatus.APPROVED,
        delivers=delivers,
    )
    return owner, shop


class VendorOrderAccessTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner, self.shop = make_shop("mine")
        self.other_owner, self.other_shop = make_shop("theirs")
        self.customer = User.objects.create_user(
            email="buyer@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.product = Product.objects.create(
            business=self.shop, name="Rice", price=Decimal("1000.00"), stock=10, is_active=True
        )
        add_to_cart(customer=self.customer, product_id=self.product.id, quantity=1)
        group = checkout_cart(customer=self.customer)  # shop doesn't deliver -> pickup
        self.order = group.orders.get()

    def pay(self):
        self.order.status = OrderStatus.PAID
        self.order.save(update_fields=["status"])

    # ─── Listing ──────────────────────────────────────────────────────────────

    def test_vendor_sees_their_own_shops_orders(self):
        self.client.force_authenticate(self.owner)
        res = self.client.get("/api/orders/")
        ids = [o["id"] for o in res.data["results"]]
        self.assertIn(str(self.order.id), ids)

    def test_vendor_does_not_see_another_shops_orders(self):
        self.client.force_authenticate(self.other_owner)
        res = self.client.get("/api/orders/")
        ids = [o["id"] for o in res.data["results"]]
        self.assertNotIn(str(self.order.id), ids)

    def test_an_order_appears_once_even_with_several_lines(self):
        """The old query joined through line items and could repeat an order."""
        second = Product.objects.create(
            business=self.shop, name="Beans", price=Decimal("500.00"), stock=10, is_active=True
        )
        add_to_cart(customer=self.customer, product_id=self.product.id, quantity=1)
        add_to_cart(customer=self.customer, product_id=second.id, quantity=1)
        checkout_cart(customer=self.customer)
        self.client.force_authenticate(self.owner)
        res = self.client.get("/api/orders/")
        ids = [o["id"] for o in res.data["results"]]
        self.assertEqual(len(ids), len(set(ids)))

    # ─── Marking ready for collection ─────────────────────────────────────────

    def test_owner_can_mark_their_order_ready(self):
        self.pay()
        self.client.force_authenticate(self.owner)
        res = self.client.post(f"/api/orders/{self.order.id}/ready-for-pickup/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "ready_for_pickup")
        self.assertTrue(res.data["pickup_code"])

    def test_another_vendor_cannot_mark_it_ready(self):
        self.pay()
        self.client.force_authenticate(self.other_owner)
        res = self.client.post(f"/api/orders/{self.order.id}/ready-for-pickup/")
        self.assertEqual(res.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PAID)

    # ─── Confirming collection ────────────────────────────────────────────────

    def ready(self):
        self.pay()
        self.client.force_authenticate(self.owner)
        self.client.post(f"/api/orders/{self.order.id}/ready-for-pickup/")
        self.order.refresh_from_db()
        return self.order.pickup_code

    def test_owner_can_confirm_collection_with_the_code(self):
        code = self.ready()
        res = self.client.post(
            f"/api/orders/{self.order.id}/confirm-pickup/", {"pickup_code": code}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "collected")

    def test_wrong_code_is_refused(self):
        self.ready()
        res = self.client.post(
            f"/api/orders/{self.order.id}/confirm-pickup/", {"pickup_code": "SM-0000"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_another_vendor_cannot_confirm_collection_even_with_the_code(self):
        code = self.ready()
        self.client.force_authenticate(self.other_owner)
        res = self.client.post(
            f"/api/orders/{self.order.id}/confirm-pickup/", {"pickup_code": code}, format="json"
        )
        self.assertEqual(res.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.READY_FOR_PICKUP)

    # ─── Advancing a delivery order ───────────────────────────────────────────

    def test_another_vendor_cannot_advance_the_order(self):
        self.pay()
        self.client.force_authenticate(self.other_owner)
        res = self.client.post(
            f"/api/orders/{self.order.id}/transition/", {"status": "processing"}, format="json"
        )
        self.assertEqual(res.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PAID)

    def test_owner_can_advance_the_order(self):
        self.pay()
        self.client.force_authenticate(self.owner)
        res = self.client.post(
            f"/api/orders/{self.order.id}/transition/", {"status": "processing"}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "processing")


class PickupFlowTest(TestCase):
    """A collection order's whole journey, the way a shop actually works."""

    def setUp(self):
        self.client = APIClient()
        self.owner, self.shop = make_shop("counter")
        self.customer = User.objects.create_user(
            email="collector@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        product = Product.objects.create(
            business=self.shop, name="Charger", price=Decimal("7500.00"), stock=10, is_active=True
        )
        add_to_cart(customer=self.customer, product_id=product.id, quantity=1)
        self.order = checkout_cart(customer=self.customer).orders.get()
        self.order.status = OrderStatus.PAID
        self.order.save(update_fields=["status"])
        self.client.force_authenticate(self.owner)

    def test_prepared_then_ready_without_passing_through_packaging(self):
        res = self.client.post(
            f"/api/orders/{self.order.id}/transition/", {"status": "processing"}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)

        res = self.client.post(f"/api/orders/{self.order.id}/ready-for-pickup/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "ready_for_pickup")
        self.assertTrue(res.data["pickup_code"])

    def test_the_customer_collects_with_their_code(self):
        self.client.post(f"/api/orders/{self.order.id}/transition/", {"status": "processing"}, format="json")
        ready = self.client.post(f"/api/orders/{self.order.id}/ready-for-pickup/")
        code = ready.data["pickup_code"]

        res = self.client.post(
            f"/api/orders/{self.order.id}/confirm-pickup/", {"pickup_code": code}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "collected")

    def test_a_delivery_order_can_still_be_packed(self):
        """The delivery route must keep working."""
        self.shop.delivers = True
        self.shop.save()
        self.order.fulfilment_type = "delivery"
        self.order.save(update_fields=["fulfilment_type"])
        self.client.post(f"/api/orders/{self.order.id}/transition/", {"status": "processing"}, format="json")
        res = self.client.post(
            f"/api/orders/{self.order.id}/transition/", {"status": "packaging"}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "packaging")
