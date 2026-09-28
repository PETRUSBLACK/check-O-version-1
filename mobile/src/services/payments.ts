import { api } from "../config/api";
import { CheckoutGroup } from "./cart";

export type Provider = "paystack" | "flutterwave" | "stripe";

export interface Payment {
  id: string;
  checkout_group: string | null;
  provider: Provider;
  external_ref: string;
  status: "pending" | "success" | "failed";
  amount: string;
}

/**
 * What POST /api/payments/initiate/ returns: the payment's own fields, with the
 * gateway's page alongside them. Not nested — checked against the live endpoint.
 */
export interface StartedPayment extends Payment {
  /** Where to send the customer to pay. */
  payment_url: string;
}

export interface VerifiedPayment {
  payment: Payment;
  checkout?: CheckoutGroup;
}

export const paymentsService = {
  // POST /api/payments/initiate/ — the amount is worked out by the server
  async start(checkoutGroupId: string, provider: Provider = "paystack"): Promise<StartedPayment> {
    const { data } = await api.post<StartedPayment>("/payments/initiate/", {
      checkout_group_id: checkoutGroupId,
      provider,
    });
    return data;
  },

  /**
   * POST /api/payments/{id}/verify/ — ask the gateway whether it went through.
   *
   * The app calls this when the customer comes back from the payment page,
   * rather than waiting for the gateway's webhook: a webhook can't reach a
   * laptop at all, and even in production it may arrive after the customer is
   * already looking at the screen. Safe to call more than once.
   */
  async verify(paymentId: string): Promise<VerifiedPayment> {
    const { data } = await api.post<VerifiedPayment>(`/payments/${paymentId}/verify/`, {});
    return data;
  },
};
