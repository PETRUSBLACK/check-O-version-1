from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.businesses.models import Business, BusinessLocation, BusinessRating, BusinessStatus
from apps.cart.services.cart_service import add_to_cart, checkout
from apps.delivery.models import Shipment, ShipmentStatus, TrackingEvent
from apps.delivery.services.shipment_service import create_shipment, update_shipment_status
from apps.orders.models import Order, OrderStatus, FulfilmentType
from apps.orders.services.order_service import expire_pickup_order, transition_order_status
from apps.payments.models import Payment, PaymentStatus
from apps.products.models import Product
from apps.users.models import User, UserRole


def make_user(email, role=UserRole.CUSTOMER, password="testpass12345"):
    return User.objects.create_user(email=email, password=password, role=role)


def make_vendor(email="vendor@example.com"):
    return make_user(email, role=UserRole.VENDOR)


def make_business(owner, slug="test-shop", biz_status=BusinessStatus.APPROVED):
    return Business.objects.create(
        owner=owner, name="Test Shop", slug=slug,
        legal_name="Test Ltd", registration_number="RC1234567",
        status=biz_status,
    )


def make_product(business, price="20.00", stock=10):
    return Product.objects.create(
        business=business, name="Widget", price=price, stock=stock, is_active=True,
    )


def make_order(customer, product, fulfilment=FulfilmentType.DELIVERY):
    add_to_cart(customer=customer, product_id=product.pk, quantity=1)
    order = checkout(customer=customer)
    order.fulfilment_type = fulfilment
    order.save()
    # Mark as paid
    payment = Payment.objects.create(
        order=order, provider="paystack",
        external_ref="test-ref", amount=order.total,
        status=PaymentStatus.SUCCESS,
    )
    order.status = OrderStatus.PAID
    order.save()
    return order


class DeliveryProviderTest(TestCase):

    def test_vendor_delivery_assigns_tracking_number(self):
        from apps.delivery.providers.vendor_delivery import VendorDeliveryProvider
        provider = VendorDeliveryProvider()
        mock_shipment = type("S", (), {"pk": "test-pk"})()
        result = provider.assign(shipment=mock_shipment)
        self.assertIn("tracking_number", result)
        self.assertTrue(result["tracking_number"].startswith("VM-"))

    def test_logistics_partner_books_shipment(self):
        from apps.delivery.providers.logistics_partner import LogisticsPartnerProvider
        provider = LogisticsPartnerProvider(partner="gig")
        mock_shipment = type("S", (), {"pk": "test-pk"})()
        result = provider.book(shipment=mock_shipment)
        self.assertIn("booking_ref", result)
        self.assertTrue(result["booking_ref"].startswith("GIG-"))

    def test_kwik_estimated_hours(self):
        from apps.delivery.providers.logistics_partner import LogisticsPartnerProvider
        provider = LogisticsPartnerProvider(partner="kwik")
        result = provider.estimate_delivery()
        self.assertEqual(result["estimated_hours"], 4)


class ShipmentServiceTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)
        self.order = make_order(self.customer, self.product)

    def test_create_shipment_for_paid_order(self):
        shipment = create_shipment(order_id=self.order.pk, mode="vendor_managed")
        self.assertIsNotNone(shipment.pk)
        self.assertEqual(shipment.status, ShipmentStatus.PENDING)
        self.assertTrue(shipment.tracking_number.startswith("VM-"))

    def test_cannot_create_duplicate_shipment(self):
        create_shipment(order_id=self.order.pk, mode="vendor_managed")
        from apps.delivery.services.shipment_service import ShipmentError
        with self.assertRaises(ShipmentError):
            create_shipment(order_id=self.order.pk, mode="vendor_managed")

    def test_shipment_creates_initial_tracking_event(self):
        shipment = create_shipment(order_id=self.order.pk, mode="vendor_managed")
        self.assertEqual(shipment.tracking_events.count(), 1)
        self.assertEqual(shipment.tracking_events.first().status, ShipmentStatus.PENDING)

    def test_update_status_creates_tracking_event(self):
        shipment = create_shipment(order_id=self.order.pk, mode="vendor_managed")
        update_shipment_status(shipment_id=shipment.pk, status="processing", note="Started")
        self.assertEqual(shipment.tracking_events.count(), 2)

    def test_invalid_transition_raises_error(self):
        from apps.delivery.services.shipment_service import ShipmentError
        shipment = create_shipment(order_id=self.order.pk, mode="vendor_managed")
        with self.assertRaises(ShipmentError):
            update_shipment_status(shipment_id=shipment.pk, status="delivered")

    def test_delivered_shipment_marks_order_delivered(self):
        shipment = create_shipment(order_id=self.order.pk, mode="vendor_managed")
        update_shipment_status(shipment_id=shipment.pk, status="processing")
        update_shipment_status(shipment_id=shipment.pk, status="packaging")
        update_shipment_status(shipment_id=shipment.pk, status="pickup")
        update_shipment_status(shipment_id=shipment.pk, status="in_transit")
        update_shipment_status(shipment_id=shipment.pk, status="delivered")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.DELIVERED)


class TrackingAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)
        self.order = make_order(self.customer, self.product)

    def test_public_can_track_by_tracking_number(self):
        shipment = create_shipment(order_id=self.order.pk, mode="vendor_managed")
        res = self.client.get(f"/api/track/{shipment.tracking_number}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("tracking_events", res.data)

    def test_authenticated_can_get_shipment_tracking(self):
        shipment = create_shipment(order_id=self.order.pk, mode="vendor_managed")
        self.client.force_authenticate(self.customer)
        res = self.client.get(f"/api/shipments/{shipment.pk}/tracking/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("tracking_events", res.data)


class LocationAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)

    def test_vendor_can_set_location(self):
        self.client.force_authenticate(self.vendor)
        res = self.client.post(f"/api/businesses/{self.business.pk}/location/", {
            "latitude": "6.5244",
            "longitude": "3.3792",
            "city": "Lagos",
            "state": "Lagos",
            "full_address": "1 Lagos Island",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(BusinessLocation.objects.filter(business=self.business).exists())

    def test_nearby_shops_returns_results(self):
        BusinessLocation.objects.create(
            business=self.business,
            latitude="6.5244", longitude="3.3792",
            city="Lagos", state="Lagos",
        )
        res = self.client.get("/api/shops/nearby/?lat=6.5244&lng=3.3792&radius_km=5")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

    def test_nearby_shops_outside_radius_excluded(self):
        BusinessLocation.objects.create(
            business=self.business,
            latitude="9.0765", longitude="7.3986",  # Abuja
            city="Abuja", state="FCT",
        )
        # Search in Lagos — Abuja shop should not appear
        res = self.client.get("/api/shops/nearby/?lat=6.5244&lng=3.3792&radius_km=5")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)


class RatingAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)

    def test_customer_can_rate_after_completed_order(self):
        order = make_order(self.customer, self.product)
        order.status = OrderStatus.DELIVERED
        order.save()
        self.client.force_authenticate(self.customer)
        res = self.client.post(f"/api/businesses/{self.business.pk}/rate/", {
            "score": 5, "review": "Excellent service!"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_customer_cannot_rate_without_order(self):
        self.client.force_authenticate(self.customer)
        res = self.client.post(f"/api/businesses/{self.business.pk}/rate/", {
            "score": 5, "review": "Great!"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_can_list_ratings(self):
        BusinessRating.objects.create(
            business=self.business, customer=self.customer, score=4, review="Good"
        )
        res = self.client.get(f"/api/businesses/{self.business.pk}/ratings/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)


class PickupFlowTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.customer = make_user("cust@example.com")
        self.product = make_product(self.business)

    def test_vendor_marks_order_ready_for_pickup(self):
        order = make_order(self.customer, self.product, fulfilment=FulfilmentType.PICKUP)
        order.status = OrderStatus.PAID
        order.save()
        self.client.force_authenticate(self.vendor)
        res = self.client.post(f"/api/orders/{order.pk}/ready-for-pickup/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.READY_FOR_PICKUP)
        self.assertTrue(order.pickup_code.startswith("SM-"))
        self.assertIsNotNone(order.pickup_deadline)

    def test_vendor_confirms_pickup_with_correct_code(self):
        order = make_order(self.customer, self.product, fulfilment=FulfilmentType.PICKUP)
        order.status = OrderStatus.READY_FOR_PICKUP
        order.generate_pickup_code()
        order.set_pickup_deadline()
        order.save()
        self.client.force_authenticate(self.vendor)
        res = self.client.post(f"/api/orders/{order.pk}/confirm-pickup/", {
            "pickup_code": order.pickup_code
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.COLLECTED)

    def test_wrong_pickup_code_rejected(self):
        order = make_order(self.customer, self.product, fulfilment=FulfilmentType.PICKUP)
        order.status = OrderStatus.READY_FOR_PICKUP
        order.generate_pickup_code()
        order.set_pickup_deadline()
        order.save()
        self.client.force_authenticate(self.vendor)
        res = self.client.post(f"/api/orders/{order.pk}/confirm-pickup/", {
            "pickup_code": "SM-0000"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_pickup_releases_stock(self):
        order = make_order(self.customer, self.product, fulfilment=FulfilmentType.PICKUP)
        order.status = OrderStatus.READY_FOR_PICKUP
        order.generate_pickup_code()
        order.pickup_deadline = timezone.now() - timezone.timedelta(hours=1)
        order.save()
        stock_before = self.product.stock
        expire_pickup_order(order_id=order.pk)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock_before + 1)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.EXPIRED)
