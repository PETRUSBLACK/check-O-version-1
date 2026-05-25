"""
Paystack payment gateway adapter.

Docs: https://paystack.com/docs/api/
Test cards: https://paystack.com/docs/payments/test-payments/

Required env vars:
    PAYSTACK_SECRET_KEY  — sk_test_xxx (test) or sk_live_xxx (production)
"""

import hashlib
import hmac
import logging
from decimal import Decimal

import requests
from django.conf import settings

from .base_gateway import BaseGateway, InitiateResult, VerifyResult

logger = logging.getLogger(__name__)

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackGateway(BaseGateway):

    def __init__(self):
        self.secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        if not self.secret_key:
            logger.warning("PAYSTACK_SECRET_KEY is not set.")
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initiate(self, *, order_id: str, amount: Decimal, email: str, currency: str = "NGN") -> InitiateResult:
        """
        Initialize a Paystack transaction.
        Amount is in Naira — Paystack requires it in kobo (x100).
        """
        amount_kobo = int(amount * 100)

        payload = {
            "email": email,
            "amount": amount_kobo,
            "currency": currency,
            "reference": f"SM-{order_id}",
            "metadata": {"order_id": str(order_id), "platform": "smartmall"},
            "callback_url": f"{getattr(settings, 'FRONTEND_ORIGIN', '')}/payment/callback",
        }

        try:
            resp = requests.post(
                f"{PAYSTACK_BASE_URL}/transaction/initialize",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("paystack_initiate_failed order=%s error=%s", order_id, exc)
            raise ValueError(f"Paystack initiation failed: {exc}") from exc

        if not data.get("status"):
            raise ValueError(f"Paystack error: {data.get('message', 'Unknown error')}")

        tx_data = data["data"]
        return InitiateResult(
            external_ref=tx_data["reference"],
            payment_url=tx_data["authorization_url"],
            provider_payload=data,
        )

    def verify(self, *, external_ref: str) -> VerifyResult:
        """Verify a Paystack transaction by its reference."""
        try:
            resp = requests.get(
                f"{PAYSTACK_BASE_URL}/transaction/verify/{external_ref}",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("paystack_verify_failed ref=%s error=%s", external_ref, exc)
            raise ValueError(f"Paystack verification failed: {exc}") from exc

        tx_data = data.get("data", {})
        success = tx_data.get("status") == "success"
        # Paystack returns amount in kobo — convert back to Naira
        amount = Decimal(tx_data.get("amount", 0)) / 100

        return VerifyResult(
            success=success,
            external_ref=external_ref,
            amount=amount,
            provider_payload=data,
        )

    def verify_webhook_signature(self, *, payload: bytes, signature: str) -> bool:
        """
        Paystack signs webhooks with HMAC-SHA512.
        Header: X-Paystack-Signature
        """
        expected = hmac.new(
            self.secret_key.encode("utf-8"),
            payload,
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
