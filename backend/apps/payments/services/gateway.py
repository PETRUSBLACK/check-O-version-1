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

from apps.orders.models import CheckoutGroup, Order, OrderStatus
from apps.orders.services.order_service import OrderFlowError, mark_order_paid
from apps.payments.models import Payment, PaymentProvider, PaymentStatus
from .registry import get_gateway

logger = logging.getLogger(__name__)

_VALID_PROVIDERS = {c.value for c in PaymentProvider}


@transaction.atomic
def initiate_checkout_payment(
    *,
    checkout_group_id: UUID,
    provider: str,
) -> tuple[Payment, str]:
    """
    Initiate ONE payment for a whole checkout (all its shop orders).

    The amount is worked out here from the orders still awaiting payment —
    never taken from the client. Orders the customer already cancelled are
    left out.
    """
    if provider not in _VALID_PROVIDERS:
        raise ValueError(f"Invalid provider '{provider}'.")

    group = CheckoutGroup.objects.select_for_update().select_related("customer").get(pk=checkout_group_id)

    if Payment.objects.filter(checkout_group=group, status=PaymentStatus.SUCCESS).exists():
        raise ValueError("This checkout has already been paid.")

    pending = list(
        Order.objects.select_for_update()
        .filter(checkout_group=group, status=OrderStatus.PENDING_PAYMENT.value)
    )
    if not pending:
        raise ValueError("None of the orders in this checkout are awaiting payment.")

    amount = sum((o.total for o in pending), Decimal("0.00"))
    gateway = get_gateway(provider)

    try:
        result = gateway.initiate(
            order_id=str(group.pk),
            amount=amount,
            email=group.customer.email,
        )
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("gateway_initiate_error provider=%s checkout=%s", provider, group.pk)
        raise ValueError(f"Payment initiation failed: {exc}") from exc

    payment = Payment.objects.create(
        checkout_group=group,
        provider=provider,
        amount=amount,
        external_ref=result.external_ref,
        status=PaymentStatus.PENDING,
    )

    logger.info(
        "payment_initiated id=%s provider=%s checkout=%s orders=%d ref=%s",
        payment.pk, provider, group.pk, len(pending), result.external_ref,
    )

    return payment, result.payment_url


def _mark_orders_paid(payment: Payment) -> None:
    """Mark every order this payment covers as paid (or flag refunds for late ones)."""
    for order in payment.get_orders():
        try:
            mark_order_paid(order_id=order.pk, payment_started_at=payment.created_at)
        except OrderFlowError as exc:
            logger.error("order_transition_failed after payment order=%s error=%s", order.pk, exc)


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

    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise ValueError("This order is no longer awaiting payment.")

    if order.checkout_group_id and order.checkout_group.orders.count() > 1:
        raise ValueError(
            "This order is part of a checkout with several shops. "
            "Pay for the whole checkout instead."
        )

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
        .select_related("order", "checkout_group")
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

    _mark_orders_paid(payment)

    # Fire payment confirmed notification (once per payment)
    try:
        from apps.notifications.services.notification_service import notify_payment_confirmed
        orders = payment.get_orders()
        if orders:
            notify_payment_confirmed(order=orders[0], payment=payment)
    except Exception:
        pass

    logger.info(
        "payment_confirmed id=%s provider=%s order=%s checkout=%s ref=%s",
        payment.pk, provider, payment.order_id, payment.checkout_group_id, external_ref,
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
    _mark_orders_paid(payment)
    return payment
