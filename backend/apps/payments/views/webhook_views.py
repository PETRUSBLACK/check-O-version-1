"""
Payment webhook views.

Each gateway calls a different endpoint with a different signature scheme.
All webhooks:
  1. Verify the signature first — reject anything that doesn't match
  2. Parse the event type
  3. Call the appropriate gateway service function
  4. Return 200 immediately (gateways retry on non-200)

Endpoints:
  POST /api/payments/webhooks/paystack/
  POST /api/payments/webhooks/flutterwave/
  POST /api/payments/webhooks/stripe/
"""

import json
import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.services.gateway import confirm_payment_via_webhook, mark_payment_failed
from apps.payments.services.registry import get_gateway

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class PaystackWebhookView(APIView):
    """
    Receives Paystack webhook events.
    Paystack signs payloads with HMAC-SHA512.
    Header: X-Paystack-Signature
    """
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.headers.get("X-Paystack-Signature", "")
        payload = request.body

        gateway = get_gateway("paystack")
        if not gateway.verify_webhook_signature(payload=payload, signature=signature):
            logger.warning("paystack_webhook_invalid_signature")
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get("event", "")
        data = event.get("data", {})
        external_ref = data.get("reference", "")

        logger.info("paystack_webhook event=%s ref=%s", event_type, external_ref)

        try:
            if event_type == "charge.success":
                confirm_payment_via_webhook(provider="paystack", external_ref=external_ref)

            elif event_type in ("charge.failed", "transfer.failed"):
                mark_payment_failed(provider="paystack", external_ref=external_ref)

        except ValueError as exc:
            # Log but still return 200 — prevents Paystack from retrying indefinitely
            logger.error("paystack_webhook_processing_error ref=%s error=%s", external_ref, exc)

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name="dispatch")
class FlutterwaveWebhookView(APIView):
    """
    Receives Flutterwave webhook events.
    Flutterwave signs with a secret hash.
    Header: verif-hash
    """
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.headers.get("Verif-Hash", "")
        payload = request.body

        gateway = get_gateway("flutterwave")
        if not gateway.verify_webhook_signature(payload=payload, signature=signature):
            logger.warning("flutterwave_webhook_invalid_signature")
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get("event", "")
        data = event.get("data", {})
        external_ref = data.get("tx_ref", "")

        logger.info("flutterwave_webhook event=%s ref=%s", event_type, external_ref)

        try:
            if event_type == "charge.completed" and data.get("status") == "successful":
                confirm_payment_via_webhook(provider="flutterwave", external_ref=external_ref)

            elif event_type == "charge.completed" and data.get("status") == "failed":
                mark_payment_failed(provider="flutterwave", external_ref=external_ref)

        except ValueError as exc:
            logger.error("flutterwave_webhook_processing_error ref=%s error=%s", external_ref, exc)

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """
    Receives Stripe webhook events.
    Stripe signs with HMAC-SHA256 + timestamp.
    Header: Stripe-Signature
    """
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.headers.get("Stripe-Signature", "")
        payload = request.body

        gateway = get_gateway("stripe")
        if not gateway.verify_webhook_signature(payload=payload, signature=signature):
            logger.warning("stripe_webhook_invalid_signature")
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get("type", "")
        data = event.get("data", {}).get("object", {})
        # Stripe session ID is the external_ref we stored
        external_ref = data.get("id", "")

        logger.info("stripe_webhook event=%s ref=%s", event_type, external_ref)

        try:
            if event_type == "checkout.session.completed":
                if data.get("payment_status") == "paid":
                    confirm_payment_via_webhook(provider="stripe", external_ref=external_ref)

            elif event_type == "checkout.session.expired":
                mark_payment_failed(provider="stripe", external_ref=external_ref)

            elif event_type == "payment_intent.payment_failed":
                # payment_intent may link back to a session — best effort
                mark_payment_failed(provider="stripe", external_ref=external_ref)

        except ValueError as exc:
            logger.error("stripe_webhook_processing_error ref=%s error=%s", external_ref, exc)

        return Response({"status": "ok"}, status=status.HTTP_200_OK)
