"""
Flutterwave payment gateway adapter.

Docs: https://developer.flutterwave.com/docs/
Test cards: https://developer.flutterwave.com/docs/integration-guides/testing-helpers/

Required env vars:
    FLUTTERWAVE_SECRET_KEY  — FLWSECK_TEST-xxx (test) or FLWSECK-xxx (production)
"""

import hashlib
import hmac
import logging
from decimal import Decimal

import requests
from django.conf import settings

from .base_gateway import BaseGateway, InitiateResult, VerifyResult

logger = logging.getLogger(__name__)

FLUTTERWAVE_BASE_URL = "https://api.flutterwave.com/v3"


class FlutterwaveGateway(BaseGateway):

    def __init__(self):
        self.secret_key = getattr(settings, "FLUTTERWAVE_SECRET_KEY", "")
        if not self.secret_key:
            logger.warning("FLUTTERWAVE_SECRET_KEY is not set.")
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initiate(self, *, order_id: str, amount: Decimal, email: str, currency: str = "NGN") -> InitiateResult:
        """
        Create a Flutterwave payment link.
        Amount is in the base currency unit (Naira for NGN).
        """
        tx_ref = f"SM-{order_id}"

        payload = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": currency,
            "redirect_url": f"{getattr(settings, 'FRONTEND_ORIGIN', '')}/payment/callback",
            "customer": {
                "email": email,
            },
            "meta": {
                "order_id": str(order_id),
                "platform": "smartmall",
            },
            "customizations": {
                "title": "SmartMall Payment",
                "logo": getattr(settings, "BRAND_LOGO_URL", ""),
            },
        }

        try:
            resp = requests.post(
                f"{FLUTTERWAVE_BASE_URL}/payments",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("flutterwave_initiate_failed order=%s error=%s", order_id, exc)
            raise ValueError(f"Flutterwave initiation failed: {exc}") from exc

        if data.get("status") != "success":
            raise ValueError(f"Flutterwave error: {data.get('message', 'Unknown error')}")

        return InitiateResult(
            external_ref=tx_ref,
            payment_url=data["data"]["link"],
            provider_payload=data,
        )

    def verify(self, *, external_ref: str) -> VerifyResult:
        """Verify a Flutterwave transaction by its tx_ref."""
        try:
            resp = requests.get(
                f"{FLUTTERWAVE_BASE_URL}/transactions",
                params={"tx_ref": external_ref},
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("flutterwave_verify_failed ref=%s error=%s", external_ref, exc)
            raise ValueError(f"Flutterwave verification failed: {exc}") from exc

        transactions = data.get("data", [])
        if not transactions:
            return VerifyResult(
                success=False,
                external_ref=external_ref,
                amount=Decimal("0"),
                provider_payload=data,
            )

        tx = transactions[0]
        success = tx.get("status") == "successful"
        amount = Decimal(str(tx.get("amount", 0)))

        return VerifyResult(
            success=success,
            external_ref=external_ref,
            amount=amount,
            provider_payload=data,
        )

    def verify_webhook_signature(self, *, payload: bytes, signature: str) -> bool:
        """
        Flutterwave signs webhooks using a secret hash.
        Header: verif-hash
        The header value must match FLUTTERWAVE_WEBHOOK_SECRET exactly.
        """
        webhook_secret = getattr(settings, "FLUTTERWAVE_WEBHOOK_SECRET", "")
        return hmac.compare_digest(webhook_secret, signature)
