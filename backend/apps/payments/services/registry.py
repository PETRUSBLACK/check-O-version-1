"""
Gateway registry.
Resolves a provider string to the correct gateway instance.
"""

from apps.payments.models import PaymentProvider
from .paystack import PaystackGateway
from .flutterwave import FlutterwaveGateway
from .stripe import StripeGateway
from .base_gateway import BaseGateway


_REGISTRY = {
    PaymentProvider.PAYSTACK: PaystackGateway,
    PaymentProvider.FLUTTERWAVE: FlutterwaveGateway,
    PaymentProvider.STRIPE: StripeGateway,
}


def get_gateway(provider: str) -> BaseGateway:
    """
    Return an instantiated gateway for the given provider string.
    Raises ValueError for unknown providers.
    """
    gateway_class = _REGISTRY.get(provider)
    if not gateway_class:
        valid = ", ".join(_REGISTRY.keys())
        raise ValueError(f"Unknown payment provider '{provider}'. Valid options: {valid}")
    return gateway_class()
