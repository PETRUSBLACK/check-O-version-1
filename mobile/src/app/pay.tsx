import { Feather } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button, EmptyState } from "../components/ui";
import { errorMessage } from "../config/api";
import { useStatusBar } from "../hooks/useStatusBar";
import { checkoutService } from "../services/checkout";
import { paymentsService } from "../services/payments";
import { colors, fonts, naira } from "../theme";

/** Where Paystack sends the customer once they're done — back into the app. */
const RETURN_TO = "checko://payment/callback";

type Stage = "ready" | "paying" | "checking" | "done" | "problem";

export default function Pay() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [stage, setStage] = useState<Stage>("ready");
  const [problem, setProblem] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);

  const checkout = useQuery({
    queryKey: ["checkout", id],
    queryFn: () => checkoutService.get(id),
  });

  const verify = useMutation({
    mutationFn: (payment: string) => paymentsService.verify(payment),
    onSuccess: (result) => {
      if (result.payment.status === "success") {
        queryClient.invalidateQueries({ queryKey: ["orders"] });
        queryClient.invalidateQueries({ queryKey: ["checkout", id] });
        setStage("done");
        router.replace({ pathname: "/order-placed", params: { id, paid: "1" } });
        return;
      }
      setStage("problem");
      setProblem("That payment hasn't come through. You can try again.");
    },
    onError: (e) => {
      setStage("problem");
      setProblem(errorMessage(e));
    },
  });

  const pay = async () => {
    setProblem(null);
    setStage("paying");
    try {
      const started = await paymentsService.start(id);
      setPaymentId(started.id);

      // Opens the payment page inside the app and hands control back the moment
      // Paystack redirects to our scheme.
      const result = await WebBrowser.openAuthSessionAsync(started.payment_url, RETURN_TO);

      if (result.type === "cancel" || result.type === "dismiss") {
        // They closed it. They may still have paid, so ask rather than assume.
        setStage("checking");
        verify.mutate(started.id);
        return;
      }

      setStage("checking");
      verify.mutate(started.id);
    } catch (e) {
      setStage("problem");
      setProblem(errorMessage(e));
    }
  };

  if (checkout.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  if (checkout.isError) {
    return (
      <View style={[styles.centre, { paddingHorizontal: 20, gap: 14 }]}>
        <EmptyState icon="alert-circle" title="Couldn't open this payment" body={errorMessage(checkout.error)} />
        <Button title="Go to my orders" onPress={() => router.replace("/orders")} />
      </View>
    );
  }

  const group = checkout.data;
  const busy = stage === "paying" || stage === "checking";

  return (
    <View style={{ flex: 1, backgroundColor: colors.sand }}>
      <ScrollView
        contentContainerStyle={{
          paddingHorizontal: 20,
          paddingTop: insets.top + 28,
          paddingBottom: 28,
          gap: 18,
        }}
      >
        <View style={{ gap: 6, alignItems: "center" }}>
          <View style={styles.badge}>
            <Feather name="lock" size={26} color={colors.leaf} />
          </View>
          <Text style={styles.title}>Pay for your order</Text>
          <Text style={styles.subtitle}>
            {group.order_count === 1
              ? "One shop, one payment."
              : `${group.order_count} shops, one payment. Each shop sends its own part.`}
          </Text>
        </View>

        <View style={styles.card}>
          {group.orders.map((order) => (
            <View key={order.id} style={styles.line}>
              <Text style={styles.shop} numberOfLines={1}>
                {order.business_name}
              </Text>
              <Text style={styles.lineValue}>{naira(order.total)}</Text>
            </View>
          ))}
          <View style={styles.rule} />
          <View style={styles.line}>
            <Text style={styles.totalLabel}>To pay</Text>
            <Text style={styles.totalValue}>{naira(group.amount_due)}</Text>
          </View>
        </View>

        {stage === "checking" ? (
          <Banner tone="info" icon="refresh-cw">
            Checking your payment with the bank. This takes a moment.
          </Banner>
        ) : null}

        {problem ? <Banner tone="danger" icon="alert-circle">{problem}</Banner> : null}

        <Text style={styles.hold}>
          Your items are held while you pay. If the payment doesn't finish within 30 minutes of
          ordering, they go back to the shops.
        </Text>
      </ScrollView>

      <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 14) }]}>
        {stage === "problem" && paymentId ? (
          <>
            <Button
              title="Check again"
              variant="secondary"
              loading={verify.isPending}
              onPress={() => {
                setStage("checking");
                setProblem(null);
                verify.mutate(paymentId);
              }}
            />
            <Button title="Try paying again" onPress={pay} />
          </>
        ) : (
          <Button
            title={`Pay ${naira(group.amount_due)}`}
            icon="credit-card"
            loading={busy}
            onPress={pay}
          />
        )}
        <Button title="Not now" variant="secondary" onPress={() => router.replace("/orders")} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  badge: {
    width: 62,
    height: 62,
    borderRadius: 31,
    backgroundColor: colors.mint,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  title: { fontFamily: fonts.display, fontSize: 25, color: colors.ink, letterSpacing: -0.5 },
  subtitle: {
    fontFamily: fonts.body,
    fontSize: 14.5,
    lineHeight: 21,
    color: colors.muted,
    textAlign: "center",
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 16,
    gap: 9,
  },
  line: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 12 },
  shop: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 14.5, color: colors.muted },
  lineValue: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  rule: { height: 1, backgroundColor: colors.line, marginVertical: 2 },
  totalLabel: { flex: 1, fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  totalValue: { fontFamily: fonts.displayBold, fontSize: 22, color: colors.ink },
  hold: {
    fontFamily: fonts.body,
    fontSize: 12.5,
    lineHeight: 18,
    color: colors.muted,
    textAlign: "center",
  },
  bar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.line,
    gap: 10,
  },
});
