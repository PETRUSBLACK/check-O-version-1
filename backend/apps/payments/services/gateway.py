"""
Payment gateway service layer.
All payment operations go through here — views never touch gateway adapters directly.

Flow:
  initiate_payment()  → calls provider API → returns payment URL to customer
  confirm_payment()   → called by webhook handler → verifies + marks order paid
  mark_payment_failed() → called by webhook handler on failure
"""

import logging
from decimal import Decimal
from uuid import UUID

from django.db import transaction

from apps.orders.models import Order, OrderStatus
from apps.orders.services.order_service import OrderFlowError, transition_order_status
from apps.payments.models import Payment, PaymentProvider, PaymentStatus
from .registry import get_gateway

logger = logging.getLogger(__name__)

_VALID_PROVIDERS = {c.value for c in PaymentProvider}


@transaction.atomic
def initiate_payment(
    *,
    order_id: UUID,
    provider: str,
    amount: Decimal,
) -> tuple[Payment, str]:
    """
    Initiate a payment for an order.

    Returns a (Payment, payment_url) tuple.
    The payment_url is where the customer should be redirected to complete payment.

    Raises ValueError if:
    - Provider is invalid
    - Order is already paid
    - Gateway API call fails
    """
    if provider not in _VALID_PROVIDERS:
        raise ValueError(f"Invalid provider '{provider}'.")

    order = Order.objects.select_for_update().select_related("customer").get(pk=order_id)

    if Payment.objects.filter(order_id=order_id, status=PaymentStatus.SUCCESS).exists():
        raise ValueError("This order has already been paid.")

    gateway = get_gateway(provider)

    try:
        result = gateway.initiate(
            order_id=str(order_id),
            amount=amount,
            email=order.customer.email,
        )
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("gateway_initiate_error provider=%s order=%s", provider, order_id)
        raise ValueError(f"Payment initiation failed: {exc}") from exc

    payment = Payment.objects.create(
        order_id=order_id,
        provider=provider,
        amount=amount,
        external_ref=result.external_ref,
        status=PaymentStatus.PENDING,
    )

    logger.info(
        "payment_initiated id=%s provider=%s order=%s ref=%s",
        payment.pk, provider, order_id, result.external_ref,
    )

    return payment, result.payment_url


@transaction.atomic
def confirm_payment_via_webhook(*, provider: str, external_ref: str) -> Payment:
    """
    Called by the webhook handler after a successful payment notification.

    1. Fetches the pending payment by external_ref
    2. Calls the gateway to verify the transaction is genuinely successful
    3. Marks the payment as SUCCESS
    4. Transitions the order to PAID

    Raises ValueError if payment not found, already processed, or gateway rejects.
    """
    payment = (
        Payment.objects
        .select_for_update()
        .select_related("order")
        .filter(external_ref=external_ref, provider=provider)
        .first()
    )

    if not payment:
        raise ValueError(f"No pending payment found for ref={external_ref} provider={provider}")

    if payment.status == PaymentStatus.SUCCESS:
        logger.info("payment_already_confirmed ref=%s", external_ref)
        return payment

    if payment.status == PaymentStatus.FAILED:
        raise ValueError(f"Payment ref={external_ref} is already marked as failed.")

    # Verify with the gateway — don't just trust the webhook payload
    gateway = get_gateway(provider)
    try:
        result = gateway.verify(external_ref=external_ref)
    except Exception as exc:
        logger.exception("gateway_verify_error provider=%s ref=%s", provider, external_ref)
        raise ValueError(f"Gateway verification failed: {exc}") from exc

    if not result.success:
        _mark_failed(payment)
        raise ValueError(f"Gateway reported payment as unsuccessful for ref={external_ref}")

    payment.status = PaymentStatus.SUCCESS
    payment.save(update_fields=["status", "updated_at"])

    try:
        transition_order_status(order_id=payment.order_id, to_status=OrderStatus.PAID.value)
    except OrderFlowError as exc:
        logger.error("order_transition_failed after payment order=%s error=%s", payment.order_id, exc)

    # Fire payment confirmed notification
    try:
        from apps.notifications.services.notification_service import notify_payment_confirmed
        notify_payment_confirmed(order=payment.order, payment=payment)
    except Exception:
        pass

    logger.info(
        "payment_confirmed id=%s provider=%s order=%s ref=%s",
        payment.pk, provider, payment.order_id, external_ref,
    )

    return payment


@transaction.atomic
def mark_payment_failed(*, provider: str, external_ref: str) -> Payment:
    """
    Called by the webhook handler when a payment failure event is received.
    """
    payment = (
        Payment.objects
        .select_for_update()
        .filter(external_ref=external_ref, provider=provider)
        .first()
    )

    if not payment:
        raise ValueError(f"No payment found for ref={external_ref}")

    return _mark_failed(payment)


def _mark_failed(payment: Payment) -> Payment:
    if payment.status in (PaymentStatus.FAILED, PaymentStatus.SUCCESS):
        return payment
    payment.status = PaymentStatus.FAILED
    payment.save(update_fields=["status", "updated_at"])
    logger.info("payment_failed id=%s ref=%s", payment.pk, payment.external_ref)
    return payment


# ─── Kept for backward compat with admin mock-confirm view ────────────────────

@transaction.atomic
def confirm_payment_success(*, payment_id: UUID) -> Payment:
    """Admin-only mock confirm. Used in dev/staging only."""
    payment = Payment.objects.select_for_update().select_related("order").get(pk=payment_id)
    if payment.status == PaymentStatus.SUCCESS:
        return payment
    if payment.status == PaymentStatus.FAILED:
        raise ValueError("Cannot confirm a failed payment.")
    payment.status = PaymentStatus.SUCCESS
    payment.save(update_fields=["status", "updated_at"])
    transition_order_status(order_id=payment.order_id, to_status=OrderStatus.PAID.value)
    return payment
