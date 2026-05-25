"""
Stripe payment gateway adapter.

Docs: https://stripe.com/docs/api
Test cards: https://stripe.com/docs/testing

Required env vars:
    STRIPE_SECRET_KEY        — sk_test_xxx (test) or sk_live_xxx (production)
    STRIPE_WEBHOOK_SECRET    — whsec_xxx (from Stripe Dashboard > Webhooks)
"""

import logging
from decimal import Decimal

import requests
from django.conf import settings

from .base_gateway import BaseGateway, InitiateResult, VerifyResult

logger = logging.getLogger(__name__)

STRIPE_BASE_URL = "https://api.stripe.com/v1"


class StripeGateway(BaseGateway):

    def __init__(self):
        self.secret_key = getattr(settings, "STRIPE_SECRET_KEY", "")
        if not self.secret_key:
            logger.warning("STRIPE_SECRET_KEY is not set.")
        self.webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
        }

    def initiate(self, *, order_id: str, amount: Decimal, email: str, currency: str = "ngn") -> InitiateResult:
        """
        Create a Stripe Checkout Session.
        Amount is in Naira — Stripe requires it in kobo/cents (x100).
        """
        amount_kobo = int(amount * 100)
        currency_lower = currency.lower()

        frontend_origin = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:3000")

        payload = {
            "mode": "payment",
            "line_items[0][price_data][currency]": currency_lower,
            "line_items[0][price_data][product_data][name]": f"SmartMall Order {order_id}",
            "line_items[0][price_data][unit_amount]": str(amount_kobo),
            "line_items[0][quantity]": "1",
            "success_url": f"{frontend_origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{frontend_origin}/payment/cancel",
            "customer_email": email,
            "metadata[order_id]": str(order_id),
            "metadata[platform]": "smartmall",
        }

        try:
            resp = requests.post(
                f"{STRIPE_BASE_URL}/checkout/sessions",
                data=payload,
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("stripe_initiate_failed order=%s error=%s", order_id, exc)
            raise ValueError(f"Stripe initiation failed: {exc}") from exc

        return InitiateResult(
            external_ref=data["id"],  # Stripe session ID
            payment_url=data["url"],
            provider_payload=data,
        )

    def verify(self, *, external_ref: str) -> VerifyResult:
        """Verify a Stripe Checkout Session by its session ID."""
        try:
            resp = requests.get(
                f"{STRIPE_BASE_URL}/checkout/sessions/{external_ref}",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("stripe_verify_failed ref=%s error=%s", external_ref, exc)
            raise ValueError(f"Stripe verification failed: {exc}") from exc

        success = data.get("payment_status") == "paid"
        # Stripe returns amount in smallest currency unit (kobo) — convert back
        amount = Decimal(data.get("amount_total", 0)) / 100

        return VerifyResult(
            success=success,
            external_ref=external_ref,
            amount=amount,
            provider_payload=data,
        )

    def verify_webhook_signature(self, *, payload: bytes, signature: str) -> bool:
        """
        Stripe signs webhooks using a HMAC-SHA256 scheme with a timestamp.
        Header: Stripe-Signature
        Format: t=timestamp,v1=signature

        We use Stripe's own library-style manual verification here
        to avoid requiring the stripe SDK as a dependency.
        """
        import hashlib
        import hmac
        import time

        try:
            parts = {k: v for k, v in (p.split("=", 1) for p in signature.split(","))}
            timestamp = parts.get("t", "")
            sig_v1 = parts.get("v1", "")

            # Reject if timestamp is older than 5 minutes (replay attack protection)
            if abs(time.time() - int(timestamp)) > 300:
                return False

            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected = hmac.new(
                self.webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(expected, sig_v1)
        except Exception:
            return False
