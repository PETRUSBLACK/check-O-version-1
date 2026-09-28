import { Feather } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { StatusPill, when } from "../(tabs)/orders";
import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { canCancel, ordersService, refundNote, statusLook } from "../../services/orders";
import { colors, fonts, naira } from "../../theme";

export default function OrderDetail() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  const order = useQuery({ queryKey: ["order", id], queryFn: () => ordersService.get(id) });

  const cancel = useMutation({
    mutationFn: () => ordersService.cancel(id),
    onSuccess: (updated) => {
      queryClient.setQueryData(["order", id], updated);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      setCancelError(null);
      setConfirming(false);
    },
    onError: (e) => setCancelError(errorMessage(e)),
  });

  if (order.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  if (order.isError) {
    return (
      <View style={[styles.centre, { paddingHorizontal: 20, gap: 14 }]}>
        <EmptyState icon="alert-circle" title="Couldn't open this order" body={errorMessage(order.error)} />
        <Button title="Back to orders" variant="secondary" onPress={() => router.replace("/orders")} />
      </View>
    );
  }

  const data = order.data;
  const look = statusLook(data);
  const refund = refundNote(data);
  const collecting = data.fulfilment_type === "pickup";
  const showCode = collecting && data.pickup_code && data.status !== "cancelled";

  return (
    <View style={{ flex: 1, backgroundColor: colors.sand }}>
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Back"
          onPress={() => (router.canGoBack() ? router.back() : router.replace("/orders"))}
          style={styles.back}
        >
          <Feather name="chevron-left" size={22} color={colors.ink} />
        </Pressable>
        <Text style={styles.title} numberOfLines={1}>
          {data.business_name ?? "Order"}
        </Text>
      </View>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 28, gap: 16 }}>
        {/* Where it's up to */}
        <View style={styles.card}>
          <View style={styles.statusRow}>
            <StatusPill look={look} />
            <Text style={styles.placed}>Ordered {when(data.created_at)}</Text>
          </View>
          {look.detail ? <Text style={styles.detail}>{look.detail}</Text> : null}
          {refund ? <Banner tone="info" icon="refresh-cw">{refund}</Banner> : null}
        </View>

        {/* Collection code — the thing they'll open this screen for */}
        {showCode ? (
          <View style={styles.codeCard}>
            <Text style={styles.codeLabel}>Show this at the shop</Text>
            <Text style={styles.codeValue}>{data.pickup_code}</Text>
            {data.pickup_deadline ? (
              <Text style={styles.codeNote}>
                Collect by {new Date(data.pickup_deadline).toLocaleDateString("en-NG", {
                  weekday: "long",
                  day: "numeric",
                  month: "short",
                })}
              </Text>
            ) : null}
          </View>
        ) : null}

        {/* What's in it */}
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>What you ordered</Text>
          {data.items.map((item) => (
            <View key={item.id} style={styles.line}>
              <Text style={styles.qty}>{item.quantity}×</Text>
              <Text style={styles.itemName} numberOfLines={2}>
                {item.product_name}
              </Text>
              <Text style={styles.itemPrice}>
                {naira(Number(item.unit_price) * item.quantity)}
              </Text>
            </View>
          ))}

          <View style={styles.rule} />
          <Row label="Items" value={naira(data.items_total)} />
          {Number(data.delivery_fee) > 0 ? (
            <Row label="Delivery" value={naira(data.delivery_fee)} />
          ) : null}
          <Row label="Total" value={naira(data.total)} strong />
        </View>

        {/* Where it's going */}
        {!collecting && data.delivery_address ? (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Delivering to</Text>
            <Text style={styles.address}>{data.delivery_address}</Text>
            <Text style={styles.recipient}>
              {data.recipient_name}
              {data.delivery_phone ? ` · ${data.delivery_phone}` : ""}
            </Text>
          </View>
        ) : null}

        {/* A customer who chose "pay later" needs the way back. */}
        {data.status === "pending_payment" && data.checkout_group ? (
          <Button
            title="Pay for this order"
            icon="credit-card"
            onPress={() =>
              router.push({ pathname: "/pay", params: { id: data.checkout_group! } })
            }
          />
        ) : null}

        {cancelError ? <Banner tone="danger" icon="alert-circle">{cancelError}</Banner> : null}

        {canCancel(data) ? (
          confirming ? (
            // Asked in the page rather than an OS dialog: it looks like the rest
            // of the app, and the consequence is spelled out where it's read.
            <View style={styles.confirm}>
              <Text style={styles.confirmTitle}>Cancel this order?</Text>
              <Text style={styles.confirmBody}>
                The items go back to {data.business_name ?? "the shop"}.
                {data.paid_at ? " Your refund will be processed." : ""}
              </Text>
              <View style={{ flexDirection: "row", gap: 10 }}>
                <Button
                  title="Keep it"
                  variant="secondary"
                  style={{ flex: 1 }}
                  onPress={() => setConfirming(false)}
                />
                <Button
                  title="Yes, cancel"
                  variant="danger"
                  style={{ flex: 1 }}
                  loading={cancel.isPending}
                  onPress={() => cancel.mutate()}
                />
              </View>
            </View>
          ) : (
            <Button
              title="Cancel this order"
              variant="danger"
              onPress={() => setConfirming(true)}
            />
          )
        ) : null}

        {data.status === "cancelled" ? null : canCancel(data) ? null : (
          <Text style={styles.noCancel}>
            The shop has started on this order, so it can't be cancelled here. Call them if
            something's wrong.
          </Text>
        )}
      </ScrollView>
    </View>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <View style={styles.row}>
      <Text style={[styles.rowLabel, strong && { fontFamily: fonts.bodyBold, color: colors.ink }]}>
        {label}
      </Text>
      <Text style={[styles.rowValue, strong && { fontFamily: fonts.displayBold, fontSize: 19 }]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 20,
    paddingBottom: 14,
  },
  back: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { flex: 1, fontFamily: fonts.display, fontSize: 23, color: colors.ink, letterSpacing: -0.5 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 16,
    gap: 9,
  },
  statusRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  placed: { fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.muted },
  detail: { fontFamily: fonts.body, fontSize: 14, lineHeight: 20, color: colors.muted },
  codeCard: {
    backgroundColor: colors.mint,
    borderRadius: 18,
    paddingVertical: 20,
    alignItems: "center",
    gap: 4,
  },
  codeLabel: { fontFamily: fonts.bodySemibold, fontSize: 13, color: colors.leaf },
  codeValue: { fontFamily: fonts.displayBold, fontSize: 30, color: colors.forest, letterSpacing: 4 },
  codeNote: { fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.leaf, marginTop: 2 },
  sectionTitle: { fontFamily: fonts.displayBold, fontSize: 16.5, color: colors.ink },
  line: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  qty: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.muted, minWidth: 26 },
  itemName: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 14.5, lineHeight: 20, color: colors.ink },
  itemPrice: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  rule: { height: 1, backgroundColor: colors.line, marginVertical: 3 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 12 },
  rowLabel: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 14, color: colors.muted },
  rowValue: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  address: { fontFamily: fonts.body, fontSize: 14.5, lineHeight: 21, color: colors.ink },
  recipient: { fontFamily: fonts.bodyMedium, fontSize: 13.5, color: colors.muted },
  confirm: {
    backgroundColor: colors.redSoft,
    borderRadius: 18,
    padding: 16,
    gap: 10,
  },
  confirmTitle: { fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.red },
  confirmBody: { fontFamily: fonts.body, fontSize: 14, lineHeight: 20, color: colors.red },
  noCancel: {
    fontFamily: fonts.body,
    fontSize: 13,
    lineHeight: 19,
    color: colors.muted,
    textAlign: "center",
    paddingHorizontal: 8,
  },
});
