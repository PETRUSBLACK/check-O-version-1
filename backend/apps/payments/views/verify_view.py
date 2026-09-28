"""
Checking a payment the moment the customer comes back from the gateway.

Paystack confirms payments by calling a webhook. That works in production, but
a webhook cannot reach a laptop, and even in production a customer who pays and
returns immediately would sit looking at "unpaid" until the webhook lands.

So the app asks us directly when it comes back, and we ask the gateway. Nothing
here trusts the app: the customer says only "check this payment", and the
gateway has the final word on whether it succeeded.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.serializers import CheckoutGroupSerializer
from apps.payments.models import Payment, PaymentStatus
from apps.payments.serializers import PaymentSerializer
from apps.payments.services.gateway import confirm_payment_via_webhook


class VerifyPaymentView(APIView):
    """Workflow: ask the gateway whether this payment went through."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: PaymentSerializer},
        tags=["payments"],
        summary="Check a payment with the gateway",
        description=(
            "Called by the app when the customer returns from the payment page. "
            "Asks the gateway directly rather than waiting for its webhook, which "
            "cannot reach a machine with no public address. Safe to call more than "
            "once — a payment already confirmed is simply returned as it is."
        ),
    )
    def post(self, request, pk=None):
        payment = (
            Payment.objects.select_related("order", "checkout_group")
            .filter(pk=pk)
            .first()
        )
        if not payment:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        if not _may_check(request.user, payment):
            return Response({"detail": "This is not your payment."}, status=status.HTTP_403_FORBIDDEN)

        if payment.status == PaymentStatus.SUCCESS:
            return Response(_body(payment, request))

        try:
            payment = confirm_payment_via_webhook(
                provider=payment.provider, external_ref=payment.external_ref
            )
        except ValueError as exc:
            # Not paid (yet), or the gateway refused it. Either way the customer
            # needs to know plainly, not to see a stack trace.
            payment.refresh_from_db()
            return Response(
                {
                    "detail": _explain(payment, str(exc)),
                    "payment": PaymentSerializer(payment).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(_body(payment, request))


def _may_check(user, payment: Payment) -> bool:
    if user.is_staff or getattr(user, "role", None) == "admin":
        return True
    if payment.checkout_group_id:
        return payment.checkout_group.customer_id == user.id
    if payment.order_id:
        return payment.order.customer_id == user.id
    return False


def _body(payment: Payment, request):
    data = {"payment": PaymentSerializer(payment).data}
    if payment.checkout_group_id:
        data["checkout"] = CheckoutGroupSerializer(
            payment.checkout_group, context={"request": request}
        ).data
    return data


def _explain(payment: Payment, error: str) -> str:
    if payment.status == PaymentStatus.FAILED:
        if "less than" in error:
            return "The amount paid was less than the total. Nothing has been charged to your order."
        return "That payment didn't go through. You can try again."
    return "We haven't seen this payment yet. If you've just paid, wait a moment and check again."
