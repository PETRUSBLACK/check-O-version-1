from django.urls import include, path

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView


# ============================================================================
# Users
# ============================================================================

from apps.users.views import (
    UserViewSet,
    RegisterView,
    MeView,
    PasswordChangeView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    LogoutView,
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)

# ============================================================================
# Businesses
# ============================================================================

from apps.businesses.views import (
    BusinessViewSet,
    BranchViewSet,
    BusinessMemberViewSet,
    SetBusinessLocationView,
    NearbyShopsView,
    RateBusinessView,
    BusinessRatingsView,
)

# ============================================================================
# Products
# ============================================================================

from apps.products.views import (
    ProductViewSet,
    ProductCategoryViewSet,
    ProductImageViewSet,
    ProductVariantViewSet,
    InventoryMovementViewSet,
    InventoryAlertViewSet,
    ProductEmbeddingViewSet,
)
from apps.products.views.inventory import (
    SetChannelAllocationView,
    AllocationStatusView,
)
# ============================================================================
# Orders
# ============================================================================

from apps.orders.views import (
    OrderViewSet,
    OrderStatusView,
    MarkReadyForPickupView,
    ConfirmPickupView,
    CancelOrderView,
    CheckoutGroupDetailView,
)

# ============================================================================
# Payments
# ============================================================================

from apps.payments.views import (
    PaymentViewSet,
    InitiatePaymentView,
    MockConfirmPaymentView,
    PaystackWebhookView,
    FlutterwaveWebhookView,
    StripeWebhookView,
)

# ============================================================================
# Delivery
# ============================================================================

from apps.delivery.views import (
    ShipmentViewSet,
    ShipmentStatusView,
    ShipmentTrackingView,
    TrackingHistoryView,
)

# ============================================================================
# Notifications
# ============================================================================

from apps.notifications.views import (
    NotificationViewSet,
)

# ============================================================================
# Subscriptions
# ============================================================================

from apps.subscriptions.views import (
    SubscriptionPlanViewSet,
    VendorSubscriptionViewSet,
    SubscribeView,
    CancelSubscriptionView,
    ActiveSubscriptionView,
)

# ============================================================================
# Promotions
# ============================================================================

from apps.ads.views import (
    ProductPromotionViewSet,
    FeaturedProductsView,
    ActiveDiscountsView,
)

# ============================================================================
# Analytics
# ============================================================================

from apps.analytics.views import (
    AnalyticsEventViewSet,
)

# ============================================================================
# AI
# ============================================================================

from apps.ai_assistant.views import (
    CustomerChatView,
    VendorChatView,
    ConversationListView,
    SmartSearchView,
    DemandForecastView,
)

# ============================================================================
# Dining
# ============================================================================

from apps.dining.views import (
    MenuView,
    MenuSectionView,
    MenuItemView,
    ToggleMenuItemView,
    DietaryFlagsView,
    MakeReservationView,
    CustomerReservationListView,
    CustomerReservationCancelView,
    VendorReservationListView,
    ConfirmReservationView,
    RejectReservationView,
    CompleteReservationView,
)

# ============================================================================
# Cart
# ============================================================================

from apps.cart.views import (
    CartViewSet,
    AddToCartView,
    UpdateCartItemView,
    RemoveFromCartView,
    CheckoutView,
)

# ============================================================================
# Router
# ============================================================================

router = DefaultRouter()

router.register(
    r"users",
    UserViewSet,
    basename="user",
)

router.register(
    r"businesses",
    BusinessViewSet,
    basename="business",
)

router.register(
    r"products",
    ProductViewSet,
    basename="product",
)

router.register(
    r"product-categories",
    ProductCategoryViewSet,
    basename="product-category",
)

router.register(
    r"product-images",
    ProductImageViewSet,
    basename="product-image",
)

router.register(
    r"product-variants",
    ProductVariantViewSet,
    basename="product-variant",
)

router.register(
    r"inventory-movements",
    InventoryMovementViewSet,
    basename="inventory-movement",
)

router.register(
    r"inventory-alerts",
    InventoryAlertViewSet,
    basename="inventory-alert",
)

router.register(
    r"product-embeddings",
    ProductEmbeddingViewSet,
    basename="product-embedding",
)

router.register(
    r"orders",
    OrderViewSet,
    basename="order",
)

router.register(
    r"payments",
    PaymentViewSet,
    basename="payment",
)

router.register(
    r"shipments",
    ShipmentViewSet,
    basename="shipment",
)

router.register(
    r"notifications",
    NotificationViewSet,
    basename="notification",
)

router.register(
    r"subscriptions",
    VendorSubscriptionViewSet,
    basename="subscription",
)

router.register(
    r"subscription-plans",
    SubscriptionPlanViewSet,
    basename="subscription-plan",
)

router.register(
    r"promotions",
    ProductPromotionViewSet,
    basename="promotion",
)

router.register(
    r"analytics-events",
    AnalyticsEventViewSet,
    basename="analytics-event",
)

router.register(
    r"cart",
    CartViewSet,
    basename="cart",
)


# ============================================================================
# Health Check
# ============================================================================

class HealthView(APIView):

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["System"],
        summary="Health Check",
        responses={
            200: OpenApiResponse(
                description="API is healthy",
            ),
        },
    )
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "smartmall-backend",
            }
        )


# ============================================================================
# URL Patterns
# ============================================================================

urlpatterns = [

    # System
    path("health/", HealthView.as_view(), name="health"),

    # Authentication
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/token/", ThrottledTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("auth/password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),

    # Business
    path("businesses/<uuid:pk>/location/", SetBusinessLocationView.as_view(), name="business-location"),
    path("businesses/<uuid:pk>/rate/", RateBusinessView.as_view(), name="business-rate"),
    path("businesses/<uuid:pk>/ratings/", BusinessRatingsView.as_view(), name="business-ratings"),
    path("shops/nearby/", NearbyShopsView.as_view(), name="nearby-shops"),

    path(
        "businesses/<uuid:business_id>/branches/",
        BranchViewSet.as_view({"get": "list", "post": "create"}),
        name="business-branch-list",
    ),

    path(
        "businesses/<uuid:business_id>/branches/<uuid:pk>/",
        BranchViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="business-branch-detail",
    ),

    path(
        "businesses/<uuid:business_id>/members/",
        BusinessMemberViewSet.as_view({"get": "list", "post": "create"}),
        name="business-member-list",
    ),

    path(
        "businesses/<uuid:business_id>/members/<uuid:pk>/",
        BusinessMemberViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="business-member-detail",
    ),

    # Cart
    path("cart/add/", AddToCartView.as_view(), name="cart-add"),
    path("cart/update/", UpdateCartItemView.as_view(), name="cart-update"),
    path("cart/remove/<uuid:product_id>/", RemoveFromCartView.as_view(), name="cart-remove"),
    path("cart/checkout/", CheckoutView.as_view(), name="cart-checkout"),

    # Products — SmartMall channel allocation
    path("products/<uuid:pk>/allocation/", SetChannelAllocationView.as_view(), name="product-allocation"),
    path("businesses/<uuid:business_id>/allocation-status/", AllocationStatusView.as_view(), name="allocation-status"),

    # Orders
    path("orders/<uuid:pk>/transition/", OrderStatusView.as_view(), name="order-transition"),
    path("orders/<uuid:pk>/ready-for-pickup/", MarkReadyForPickupView.as_view(), name="order-ready"),
    path("orders/<uuid:pk>/confirm-pickup/", ConfirmPickupView.as_view(), name="order-confirm-pickup"),
    path("orders/<uuid:pk>/cancel/", CancelOrderView.as_view(), name="order-cancel"),
    path("checkouts/<uuid:pk>/", CheckoutGroupDetailView.as_view(), name="checkout-detail"),

    # Payments
    path("payments/initiate/", InitiatePaymentView.as_view(), name="payment-initiate"),
    path("payments/<uuid:pk>/mock-confirm/", MockConfirmPaymentView.as_view(), name="payment-mock-confirm"),
    path("payments/webhooks/paystack/", PaystackWebhookView.as_view(), name="paystack-webhook"),
    path("payments/webhooks/flutterwave/", FlutterwaveWebhookView.as_view(), name="flutterwave-webhook"),
    path("payments/webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),

    # Delivery
    path("shipments/<uuid:pk>/status/", ShipmentStatusView.as_view(), name="shipment-status"),
    path("shipments/<uuid:pk>/tracking/", ShipmentTrackingView.as_view(), name="shipment-tracking"),
    path("track/<str:tracking_number>/", TrackingHistoryView.as_view(), name="tracking-history"),

    # Subscriptions
    path("subscriptions/subscribe/", SubscribeView.as_view(), name="subscription-subscribe"),
    path("subscriptions/<uuid:pk>/cancel/", CancelSubscriptionView.as_view(), name="subscription-cancel"),
    path("businesses/<uuid:business_id>/subscription/", ActiveSubscriptionView.as_view(), name="active-subscription"),

    # Promotions
    path("promotions/featured/", FeaturedProductsView.as_view(), name="featured-products"),
    path("promotions/discounts/", ActiveDiscountsView.as_view(), name="active-discounts"),

    # AI
    path("ai/chat/", CustomerChatView.as_view(), name="customer-chat"),
    path("ai/vendor-chat/", VendorChatView.as_view(), name="vendor-chat"),
    path("ai/conversations/", ConversationListView.as_view(), name="conversation-list"),
    path("ai/search/", SmartSearchView.as_view(), name="smart-search"),
    path("ai/forecast/<uuid:business_id>/", DemandForecastView.as_view(), name="forecast"),

    # Dining
    path("businesses/<uuid:business_id>/menu/", MenuView.as_view(), name="dining-menu"),
    path("businesses/<uuid:business_id>/menu/sections/<uuid:section_id>/items/", MenuItemView.as_view(), name="dining-menu-item"),
    path("businesses/<uuid:business_id>/menu/sections/<uuid:section_id>/items/<uuid:item_id>/", MenuItemView.as_view(), name="dining-menu-item-detail"),
    path("businesses/<uuid:business_id>/menu/sections/", MenuSectionView.as_view(), name="dining-menu-section"),
    path("businesses/<uuid:business_id>/menu/sections/<uuid:section_id>/", MenuSectionView.as_view(), name="dining-menu-section-detail"),
    path("businesses/<uuid:business_id>/menu/items/<uuid:item_id>/toggle/", ToggleMenuItemView.as_view(), name="dining-toggle-item"),
    path("dining/flags/", DietaryFlagsView.as_view(), name="dining-flags"),
    path("businesses/<uuid:business_id>/reservations/", MakeReservationView.as_view(), name="dining-make-reservation"),
    path("reservations/mine/", CustomerReservationListView.as_view(), name="dining-customer-list"),
    path("reservations/<uuid:reservation_id>/cancel/", CustomerReservationCancelView.as_view(), name="dining-customer-cancel"),
    path("businesses/<uuid:business_id>/reservations/list/", VendorReservationListView.as_view(), name="dining-vendor-list"),
    path("businesses/<uuid:business_id>/reservations/<uuid:reservation_id>/confirm/", ConfirmReservationView.as_view(), name="dining-confirm"),
    path("businesses/<uuid:business_id>/reservations/<uuid:reservation_id>/reject/", RejectReservationView.as_view(), name="dining-reject"),
    path("businesses/<uuid:business_id>/reservations/<uuid:reservation_id>/complete/", CompleteReservationView.as_view(), name="dining-complete"),

    # Router
    path("", include(router.urls)),
]