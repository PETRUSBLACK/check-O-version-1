"""
Platform-wide constants for SmartMall.
Always import from here — never hardcode these strings in app code.
"""


class UserRole:
    CUSTOMER = "customer"
    VENDOR = "vendor"
    ADMIN = "admin"
    ALL = (CUSTOMER, VENDOR, ADMIN)


class BusinessStatus:
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class OrderStatus:
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    PACKAGING = "packaging"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentProvider:
    PAYSTACK = "paystack"
    FLUTTERWAVE = "flutterwave"
    STRIPE = "stripe"
    ALL = (PAYSTACK, FLUTTERWAVE, STRIPE)


class PaymentStatus:
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class ShipmentStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    PACKAGING = "packaging"
    PICKUP = "pickup"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class DeliveryMode:
    VENDOR_MANAGED = "vendor_managed"
    PARTNER = "partner"


class ThrottleScope:
    AUTH_REGISTER = "auth_register"
    AUTH_TOKEN = "auth_token"
    AUTH_PASSWORD_RESET = "auth_password_reset"
    PAYMENT_WEBHOOK = "payment_webhook"


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
