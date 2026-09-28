"""
Delivery at checkout.

Check-O runs no riders. Each shop says whether it delivers and what it charges,
and the customer chooses delivery or pickup for each shop in the cart.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.businesses.choices import BusinessStatus
from apps.businesses.models import Business
from apps.cart.services.cart_service import CartError, add_to_cart, checkout_cart
from apps.orders.models import FulfilmentType, Order
from apps.products.models import Product
from apps.users.models import User, UserRole

DELIVERY = {
    "recipient_name": "Petrus O.",
    "phone": "08030000000",
    "address": "14 Okpanam Road, opposite the filling station, Asaba",
}


def make_shop(slug, name, *, delivers, fee="0.00"):
    owner = User.objects.create_user(
        email=f"{slug}@example.com", password="testpass12345", role=UserRole.VENDOR
    )
    return Business.objects.create(
        owner=owner,
        name=name,
        slug=slug,
        legal_name=name + " Ltd",
        registration_number="RC" + slug[:6].upper(),
        status=BusinessStatus.APPROVED,
        delivers=delivers,
        delivery_fee=Decimal(fee),
    )


class DeliveryCheckoutTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email="buyer@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.grocer = make_shop("grocer", "Mama Nkechi Stores", delivers=True, fee="1500.00")
        self.chemist = make_shop("chemist", "Grace Chemist", delivers=False)
        self.rice = Product.objects.create(
            business=self.grocer, name="Rice", price=Decimal("10000.00"), stock=20, is_active=True
        )
        self.tablets = Product.objects.create(
            business=self.chemist, name="Tablets", price=Decimal("700.00"), stock=20, is_active=True
        )
        self.client.force_authenticate(self.customer)

    def fill_cart(self, *, rice=1, tablets=0):
        if rice:
            add_to_cart(customer=self.customer, product_id=self.rice.id, quantity=rice)
        if tablets:
            add_to_cart(customer=self.customer, product_id=self.tablets.id, quantity=tablets)

    # ─── The fee ──────────────────────────────────────────────────────────────

    def test_delivery_fee_is_added_to_that_shops_order(self):
        self.fill_cart(rice=2)
        group = checkout_cart(
            customer=self.customer,
            fulfilment={str(self.grocer.id): "delivery"},
            delivery=DELIVERY,
        )
        order = group.orders.get()
        self.assertEqual(order.items_total, Decimal("20000.00"))
        self.assertEqual(order.delivery_fee, Decimal("1500.00"))
        self.assertEqual(order.total, Decimal("21500.00"))
        self.assertEqual(group.total, Decimal("21500.00"))

    def test_pickup_is_not_charged_a_fee(self):
        self.fill_cart(rice=2)
        group = checkout_cart(
            customer=self.customer, fulfilment={str(self.grocer.id): "pickup"}
        )
        order = group.orders.get()
        self.assertEqual(order.delivery_fee, Decimal("0.00"))
        self.assertEqual(order.total, Decimal("20000.00"))

    def test_fee_is_copied_onto_the_order_so_a_later_price_change_does_not_move_it(self):
        self.fill_cart(rice=1)
        group = checkout_cart(
            customer=self.customer,
            fulfilment={str(self.grocer.id): "delivery"},
            delivery=DELIVERY,
        )
        self.grocer.delivery_fee = Decimal("5000.00")
        self.grocer.save()
        order = group.orders.get()
        order.refresh_from_db()
        self.assertEqual(order.delivery_fee, Decimal("1500.00"))
        self.assertEqual(order.total, Decimal("11500.00"))

    def test_only_the_delivering_shop_is_charged_in_a_two_shop_checkout(self):
        self.fill_cart(rice=1, tablets=1)
        group = checkout_cart(
            customer=self.customer,
            fulfilment={str(self.grocer.id): "delivery", str(self.chemist.id): "pickup"},
            delivery=DELIVERY,
        )
        grocer_order = group.orders.get(business=self.grocer)
        chemist_order = group.orders.get(business=self.chemist)
        self.assertEqual(grocer_order.total, Decimal("11500.00"))
        self.assertEqual(chemist_order.total, Decimal("700.00"))
        self.assertEqual(group.total, Decimal("12200.00"))

    # ─── What the customer is allowed to choose ───────────────────────────────

    def test_cannot_ask_a_shop_that_does_not_deliver_to_deliver(self):
        self.fill_cart(rice=0, tablets=1)
        with self.assertRaises(CartError) as ctx:
            checkout_cart(
                customer=self.customer,
                fulfilment={str(self.chemist.id): "delivery"},
                delivery=DELIVERY,
            )
        self.assertIn("does not deliver", str(ctx.exception))

    def test_delivery_needs_a_name_phone_and_address(self):
        self.fill_cart(rice=1)
        with self.assertRaises(CartError) as ctx:
            checkout_cart(
                customer=self.customer,
                fulfilment={str(self.grocer.id): "delivery"},
                delivery={"recipient_name": "  ", "phone": "", "address": ""},
            )
        message = str(ctx.exception)
        self.assertIn("a name", message)
        self.assertIn("a phone number", message)
        self.assertIn("a delivery address", message)

    def test_pickup_only_checkout_needs_no_address(self):
        self.fill_cart(rice=0, tablets=2)
        group = checkout_cart(customer=self.customer)  # chemist doesn't deliver
        order = group.orders.get()
        self.assertEqual(order.fulfilment_type, FulfilmentType.PICKUP)
        self.assertEqual(order.delivery_address, "")
        self.assertTrue(order.pickup_code)
        self.assertIsNotNone(order.pickup_deadline)

    def test_shop_left_out_defaults_to_what_it_can_do(self):
        self.fill_cart(rice=1, tablets=1)
        group = checkout_cart(customer=self.customer, delivery=DELIVERY)
        self.assertEqual(group.orders.get(business=self.grocer).fulfilment_type, FulfilmentType.DELIVERY)
        self.assertEqual(group.orders.get(business=self.chemist).fulfilment_type, FulfilmentType.PICKUP)

    def test_delivery_details_land_on_the_order(self):
        self.fill_cart(rice=1)
        group = checkout_cart(
            customer=self.customer,
            fulfilment={str(self.grocer.id): "delivery"},
            delivery=DELIVERY,
        )
        order = group.orders.get()
        self.assertEqual(order.recipient_name, "Petrus O.")
        self.assertEqual(order.delivery_phone, "08030000000")
        self.assertIn("Okpanam Road", order.delivery_address)

    def test_a_picked_up_order_keeps_no_delivery_details(self):
        """Choosing pickup for one shop must not leak the address onto that order."""
        self.fill_cart(rice=1, tablets=1)
        group = checkout_cart(
            customer=self.customer,
            fulfilment={str(self.grocer.id): "delivery", str(self.chemist.id): "pickup"},
            delivery=DELIVERY,
        )
        chemist_order = group.orders.get(business=self.chemist)
        self.assertEqual(chemist_order.delivery_address, "")
        self.assertEqual(chemist_order.delivery_phone, "")
        self.assertEqual(chemist_order.recipient_name, "")


class CheckoutEndpointTest(TestCase):
    """The same rules, through the API the app actually calls."""

    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email="buyer2@example.com", password="testpass12345", role=UserRole.CUSTOMER
        )
        self.shop = make_shop("api-shop", "API Shop", delivers=True, fee="1200.00")
        self.product = Product.objects.create(
            business=self.shop, name="Beans", price=Decimal("5000.00"), stock=10, is_active=True
        )
        self.client.force_authenticate(self.customer)
        add_to_cart(customer=self.customer, product_id=self.product.id, quantity=2)

    def test_cart_tells_the_app_what_each_shop_can_do(self):
        res = self.client.get("/api/cart/")
        self.assertEqual(res.status_code, 200)
        shop = res.data["shops"][0]
        self.assertEqual(shop["name"], "API Shop")
        self.assertTrue(shop["delivers"])
        self.assertEqual(shop["delivery_fee"], "1200.00")

    def test_checkout_with_delivery(self):
        res = self.client.post(
            "/api/cart/checkout/",
            {"fulfilment": {str(self.shop.id): "delivery"}, "delivery": DELIVERY},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["total"], "11200.00")
        order = res.data["orders"][0]
        self.assertEqual(order["items_total"], "10000.00")
        self.assertEqual(order["delivery_fee"], "1200.00")
        self.assertEqual(order["fulfilment_type"], "delivery")

    def test_checkout_without_an_address_is_refused_and_keeps_the_cart(self):
        res = self.client.post(
            "/api/cart/checkout/", {"fulfilment": {str(self.shop.id): "delivery"}}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("delivery address", res.data["detail"])
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.client.get("/api/cart/").data["item_count"], 1)

    def test_checkout_with_pickup_returns_a_collection_code(self):
        res = self.client.post(
            "/api/cart/checkout/", {"fulfilment": {str(self.shop.id): "pickup"}}, format="json"
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["total"], "10000.00")
        self.assertTrue(res.data["orders"][0]["pickup_code"])
