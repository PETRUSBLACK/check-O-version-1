"""
Base gateway interface.
Every payment provider adapter must implement this contract.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class InitiateResult:
    """Returned by a gateway after initiating a payment."""
    external_ref: str        # Gateway's unique reference for this transaction
    payment_url: str         # URL to redirect the customer to for payment
    provider_payload: dict   # Raw response from the gateway (for logging)


@dataclass
class VerifyResult:
    """Returned by a gateway after verifying a webhook or callback."""
    success: bool            # True if payment was successful
    external_ref: str        # Gateway's reference
    amount: Decimal          # Amount confirmed by gateway
    provider_payload: dict   # Raw payload from gateway


class BaseGateway(ABC):

    @abstractmethod
    def initiate(self, *, order_id: str, amount: Decimal, email: str, currency: str = "NGN") -> InitiateResult:
        """
        Initiate a payment with the provider.
        Returns a redirect URL and an external reference.
        """
        ...

    @abstractmethod
    def verify(self, *, external_ref: str) -> VerifyResult:
        """
        Verify the status of a transaction by its external reference.
        Called after webhook receipt or redirect callback.
        """
        ...

    @abstractmethod
    def verify_webhook_signature(self, *, payload: bytes, signature: str) -> bool:
        """
        Verify that an incoming webhook was genuinely sent by the gateway.
        Must be called before processing any webhook payload.
        """
        ...
