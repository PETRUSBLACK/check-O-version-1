from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.businesses.models import Business
from apps.subscriptions.serializers import VendorSubscriptionSerializer
from apps.subscriptions.services.subscription_service import (
    SubscriptionError, subscribe, cancel_subscription, get_active_subscription
)
from core.permissions import IsVendorOrAdmin


class SubscribeView(APIView):
    """Workflow: Subscribe a business to a plan."""
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    @extend_schema(
        tags=["subscriptions"],
        summary="Subscribe business to a plan",
        description="Pass `business_id` and `plan_id`. Free plans activate immediately. Paid plans require payment.",
    )
    def post(self, request):
        business_id = request.data.get("business_id")
        plan_id = request.data.get("plan_id")
        if not business_id or not plan_id:
            return Response({"detail": "business_id and plan_id required."}, status=400)

        business = Business.objects.filter(pk=business_id).first()
        if not business:
            return Response({"detail": "Business not found."}, status=404)

        if not request.user.is_staff and getattr(request.user, "role", None) != "admin":
            if business.owner_id != request.user.id:
                return Response({"detail": "Not your business."}, status=403)

        try:
            sub = subscribe(business=business, plan_id=plan_id)
        except SubscriptionError as e:
            return Response({"detail": str(e)}, status=400)

        return Response(VendorSubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)


class CancelSubscriptionView(APIView):
    """Workflow: Cancel a subscription."""
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    @extend_schema(tags=["subscriptions"], summary="Cancel a subscription")
    def post(self, request, pk=None):
        from apps.subscriptions.models import VendorSubscription
        sub = VendorSubscription.objects.filter(pk=pk).first()
        if not sub:
            return Response({"detail": "Subscription not found."}, status=404)

        if not request.user.is_staff and getattr(request.user, "role", None) != "admin":
            if sub.business.owner_id != request.user.id:
                return Response({"detail": "Not your subscription."}, status=403)

        try:
            sub = cancel_subscription(subscription_id=sub.pk)
        except SubscriptionError as e:
            return Response({"detail": str(e)}, status=400)

        return Response(VendorSubscriptionSerializer(sub).data)


class ActiveSubscriptionView(APIView):
    """Workflow: Get active subscription for a business."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["subscriptions"], summary="Get active subscription for a business")
    def get(self, request, business_id=None):
        business = Business.objects.filter(pk=business_id).first()
        if not business:
            return Response({"detail": "Business not found."}, status=404)

        sub = get_active_subscription(business=business)
        if not sub:
            return Response({"detail": "No active subscription.", "plan": "free"})

        return Response(VendorSubscriptionSerializer(sub).data)
