import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button } from "../components/ui";
import { errorMessage } from "../config/api";
import { useStatusBar } from "../hooks/useStatusBar";
import { checkoutService } from "../services/checkout";
import { colors, fonts, naira } from "../theme";

export default function OrderPlaced() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const { id, paid } = useLocalSearchParams<{ id: string; paid?: string }>();
  const justPaid = paid === "1";

  const checkout = useQuery({
    queryKey: ["checkout", id],
    queryFn: () => checkoutService.get(id),
  });

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
        <Banner tone="danger" icon="alert-circle">{errorMessage(checkout.error)}</Banner>
        <Button title="Go to my orders" onPress={() => router.replace("/orders")} />
      </View>
    );
  }

  const group = checkout.data;

  return (
    <View style={{ flex: 1, backgroundColor: colors.sand }}>
      <ScrollView
        contentContainerStyle={{
          paddingHorizontal: 20,
          paddingTop: insets.top + 32,
          paddingBottom: 28,
          gap: 18,
        }}
      >
        <View style={styles.tick}>
          <Feather name="check" size={34} color={colors.white} />
        </View>

        <View style={{ gap: 6, alignItems: "center" }}>
          <Text style={styles.title}>{justPaid ? "Payment received" : "Order placed"}</Text>
          <Text style={styles.subtitle}>
            {justPaid
              ? group.order_count === 1
                ? "The shop has been told and will start on your order."
                : `All ${group.order_count} shops have been told and will start on your order.`
              : group.order_count === 1
                ? "Your order is waiting for payment."
                : `${group.order_count} orders, one for each shop, waiting for payment.`}
          </Text>
        </View>

        {justPaid ? null : (
          <Banner tone="warning" icon="clock">
            Your items are held for 30 minutes. If you haven't paid by then they go back to the
            shops.
          </Banner>
        )}

        <View style={{ gap: 12 }}>
          {group.orders.map((order) => (
            <View key={order.id} style={styles.card}>
              <Text style={styles.shop}>{order.business_name}</Text>

              <View style={styles.line}>
                <Text style={styles.lineLabel}>Items</Text>
                <Text style={styles.lineValue}>{naira(order.items_total)}</Text>
              </View>
              {Number(order.delivery_fee) > 0 ? (
                <View style={styles.line}>
                  <Text style={styles.lineLabel}>Delivery</Text>
                  <Text style={styles.lineValue}>{naira(order.delivery_fee)}</Text>
                </View>
              ) : null}
              <View style={[styles.line, styles.lineTop]}>
                <Text style={[styles.lineLabel, { fontFamily: fonts.bodyBold, color: colors.ink }]}>
                  Total
                </Text>
                <Text style={[styles.lineValue, { fontSize: 16 }]}>{naira(order.total)}</Text>
              </View>

              {order.fulfilment_type === "delivery" ? (
                <View style={styles.note}>
                  <Feather name="truck" size={15} color={colors.leaf} />
                  <Text style={styles.noteText}>Delivering to {order.delivery_address}</Text>
                </View>
              ) : (
                <View style={styles.pickup}>
                  <Text style={styles.pickupLabel}>Show this code when you collect</Text>
                  <Text style={styles.pickupCode}>{order.pickup_code}</Text>
                </View>
              )}
            </View>
          ))}
        </View>

        <View style={styles.totalRow}>
          <Text style={styles.totalLabel}>{justPaid ? "You paid" : "You'll pay"}</Text>
          <Text style={styles.totalValue}>{naira(group.total)}</Text>
        </View>
      </ScrollView>

      <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 14) }]}>
        {justPaid ? (
          <>
            <Button title="See my orders" onPress={() => router.replace("/orders")} />
            <Button title="Keep shopping" variant="secondary" onPress={() => router.replace("/")} />
          </>
        ) : (
          <>
            <Button
              title={`Pay ${naira(group.amount_due)}`}
              icon="credit-card"
              onPress={() => router.replace({ pathname: "/pay", params: { id } })}
            />
            <Button title="Pay later" variant="secondary" onPress={() => router.replace("/orders")} />
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  tick: {
    alignSelf: "center",
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.leaf,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { fontFamily: fonts.display, fontSize: 27, color: colors.ink, letterSpacing: -0.5 },
  subtitle: {
    fontFamily: fonts.body,
    fontSize: 15,
    lineHeight: 22,
    color: colors.muted,
    textAlign: "center",
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 16,
    gap: 7,
  },
  shop: { fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.ink, marginBottom: 2 },
  line: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" },
  lineTop: { borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 8, marginTop: 2 },
  lineLabel: { fontFamily: fonts.bodyMedium, fontSize: 14, color: colors.muted },
  lineValue: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  note: { flexDirection: "row", gap: 7, alignItems: "flex-start", marginTop: 4 },
  noteText: { flex: 1, fontFamily: fonts.body, fontSize: 13, lineHeight: 19, color: colors.muted },
  pickup: {
    marginTop: 6,
    backgroundColor: colors.mint,
    borderRadius: 14,
    paddingVertical: 12,
    alignItems: "center",
    gap: 2,
  },
  pickupLabel: { fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.leaf },
  pickupCode: {
    fontFamily: fonts.displayBold,
    fontSize: 24,
    color: colors.forest,
    letterSpacing: 3,
  },
  totalRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" },
  totalLabel: { fontFamily: fonts.bodyMedium, fontSize: 15, color: colors.muted },
  totalValue: { fontFamily: fonts.displayBold, fontSize: 22, color: colors.ink },
  bar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.line,
    gap: 10,
  },
});
