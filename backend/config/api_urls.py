from django.urls import include, path
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.views import (
    UserViewSet, RegisterView, MeView, PasswordChangeView,
    PasswordResetRequestView, PasswordResetConfirmView,
    LogoutView, ThrottledTokenObtainPairView, ThrottledTokenRefreshView,
)
from apps.businesses.views import (
    BusinessViewSet, SetBusinessLocationView,
    NearbyShopsView, RateBusinessView, BusinessRatingsView,
)
from apps.products.views import ProductViewSet, SetChannelAllocationView, AllocationStatusView
from apps.orders.views import OrderViewSet, OrderStatusView, MarkReadyForPickupView, ConfirmPickupView
from apps.payments.views import (
    PaymentViewSet, InitiatePaymentView, MockConfirmPaymentView,
    PaystackWebhookView, FlutterwaveWebhookView, StripeWebhookView,
)
from apps.delivery.views import ShipmentViewSet, ShipmentStatusView, TrackingHistoryView, ShipmentTrackingView
from apps.notifications.views import NotificationViewSet
from apps.subscriptions.views import (
    SubscriptionPlanViewSet, VendorSubscriptionViewSet,
    SubscribeView, CancelSubscriptionView, ActiveSubscriptionView,
)
from apps.ads.views import ProductPromotionViewSet, FeaturedProductsView, ActiveDiscountsView
from apps.analytics.views import AnalyticsEventViewSet
from apps.ai_assistant.views import (
    CustomerChatView,
    VendorChatView,
    ConversationListView,
    SmartSearchView,
    DemandForecastView,
)
from apps.cart.views import (
    CartViewSet, AddToCartView, UpdateCartItemView,
    RemoveFromCartView, CheckoutView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"businesses", BusinessViewSet, basename="business")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"shipments", ShipmentViewSet, basename="shipment")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"subscriptions", VendorSubscriptionViewSet, basename="subscription")
router.register(r"subscription-plans", SubscriptionPlanViewSet, basename="subscription-plan")
router.register(r"promotions", ProductPromotionViewSet, basename="promotion")
router.register(r"analytics-events", AnalyticsEventViewSet, basename="analytics-event")
router.register(r"cart", CartViewSet, basename="cart")


class HealthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["system"], summary="Health check", responses={200: OpenApiResponse(description="API is healthy")})
    def get(self, request):
        return Response({"status": "ok", "service": "smartmall-backend"})


urlpatterns = [
    # System
    path("health/", HealthView.as_view(), name="health"),

    # Auth
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="auth-password-change"),
    path("auth/password/reset/", PasswordResetRequestView.as_view(), name="auth-password-reset-request"),
    path("auth/password/reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),

    # Channel Allocation — for multi-channel vendors (supermarkets, large businesses)
    path("products/<uuid:pk>/allocation/", SetChannelAllocationView.as_view(), name="product-allocation"),
    path("businesses/<uuid:business_id>/allocation-status/", AllocationStatusView.as_view(), name="business-allocation-status"),

    # Cart
    path("cart/add/", AddToCartView.as_view(), name="cart-add"),
    path("cart/update/", UpdateCartItemView.as_view(), name="cart-update"),
    path("cart/remove/<uuid:product_id>/", RemoveFromCartView.as_view(), name="cart-remove"),
    path("cart/checkout/", CheckoutView.as_view(), name="cart-checkout"),

    # Orders
    path("orders/<uuid:pk>/transition/", OrderStatusView.as_view(), name="order-transition"),
    path("orders/<uuid:pk>/ready-for-pickup/", MarkReadyForPickupView.as_view(), name="order-ready-pickup"),
    path("orders/<uuid:pk>/confirm-pickup/", ConfirmPickupView.as_view(), name="order-confirm-pickup"),

    # Payments
    path("payments/initiate/", InitiatePaymentView.as_view(), name="payment-initiate"),
    path("payments/<uuid:pk>/mock-confirm/", MockConfirmPaymentView.as_view(), name="payment-mock-confirm"),
    path("payments/webhooks/paystack/", PaystackWebhookView.as_view(), name="webhook-paystack"),
    path("payments/webhooks/flutterwave/", FlutterwaveWebhookView.as_view(), name="webhook-flutterwave"),
    path("payments/webhooks/stripe/", StripeWebhookView.as_view(), name="webhook-stripe"),

    # Delivery & Tracking
    path("shipments/<uuid:pk>/status/", ShipmentStatusView.as_view(), name="shipment-status"),
    path("shipments/<uuid:pk>/tracking/", ShipmentTrackingView.as_view(), name="shipment-tracking"),
    path("track/<str:tracking_number>/", TrackingHistoryView.as_view(), name="tracking-public"),

    # Businesses — Location & Ratings
    path("businesses/<uuid:pk>/location/", SetBusinessLocationView.as_view(), name="business-location"),
    path("businesses/<uuid:pk>/rate/", RateBusinessView.as_view(), name="business-rate"),
    path("businesses/<uuid:pk>/ratings/", BusinessRatingsView.as_view(), name="business-ratings"),
    path("shops/nearby/", NearbyShopsView.as_view(), name="shops-nearby"),

    # Subscriptions
    path("subscriptions/subscribe/", SubscribeView.as_view(), name="subscription-subscribe"),
    path("subscriptions/<uuid:pk>/cancel/", CancelSubscriptionView.as_view(), name="subscription-cancel"),
    path("businesses/<uuid:business_id>/subscription/", ActiveSubscriptionView.as_view(), name="business-subscription"),

    # Ads & Promotions
    path("promotions/featured/", FeaturedProductsView.as_view(), name="promotions-featured"),
    path("promotions/discounts/", ActiveDiscountsView.as_view(), name="promotions-discounts"),

    # AI Assistant — Phase 5
    path("ai/chat/", CustomerChatView.as_view(), name="ai-customer-chat"),
    path("ai/vendor-chat/", VendorChatView.as_view(), name="ai-vendor-chat"),
    path("ai/conversations/", ConversationListView.as_view(), name="ai-conversations"),
    path("ai/search/", SmartSearchView.as_view(), name="ai-smart-search"),
    path("ai/forecast/<uuid:business_id>/", DemandForecastView.as_view(), name="ai-demand-forecast"),

    # Router (CRUD)
    path("", include(router.urls)),
]
