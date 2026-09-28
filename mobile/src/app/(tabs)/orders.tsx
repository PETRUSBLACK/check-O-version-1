import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { Order, ordersService, statusLook } from "../../services/orders";
import { colors, fonts, naira } from "../../theme";

export default function Orders() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();

  const orders = useQuery({ queryKey: ["orders"], queryFn: ordersService.list });

  if (orders.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.sand }}
      data={orders.data ?? []}
      keyExtractor={(o) => o.id}
      contentContainerStyle={{
        paddingHorizontal: 20,
        paddingTop: insets.top + 20,
        paddingBottom: 24,
        gap: 12,
      }}
      refreshControl={
        <RefreshControl
          refreshing={orders.isRefetching}
          onRefresh={() => orders.refetch()}
          tintColor={colors.leaf}
        />
      }
      ListHeaderComponent={
        <View style={{ gap: 12, marginBottom: 2 }}>
          <Text style={styles.title}>Your orders</Text>
          {orders.isError ? (
            <>
              <Banner tone="danger" icon="wifi-off">{errorMessage(orders.error)}</Banner>
              <Button title="Try again" variant="secondary" onPress={() => orders.refetch()} />
            </>
          ) : null}
        </View>
      }
      ListEmptyComponent={
        orders.isError ? null : (
          <EmptyState
            icon="file-text"
            title="No orders yet"
            body="When you order from a shop, it shows up here so you can follow it."
            action={
              <Button
                title="Start shopping"
                onPress={() => router.navigate("/")}
                style={{ marginTop: 8, alignSelf: "stretch" }}
              />
            }
          />
        )
      }
      renderItem={({ item }) => <OrderRow order={item} />}
    />
  );
}

function OrderRow({ order }: { order: Order }) {
  const look = statusLook(order);
  const count = order.items.reduce((total, i) => total + i.quantity, 0);
  const first = order.items[0]?.product_name ?? "";
  const rest = order.items.length - 1;

  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`Order from ${order.business_name}, ${look.label}, ${naira(order.total)}`}
      onPress={() => router.push({ pathname: "/order/[id]", params: { id: order.id } })}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.9 }]}
    >
      <View style={styles.head}>
        <Text style={styles.shop} numberOfLines={1}>
          {order.business_name ?? "Order"}
        </Text>
        <StatusPill look={look} />
      </View>

      <Text style={styles.items} numberOfLines={1}>
        {first}
        {rest > 0 ? ` and ${rest} more` : ""}
      </Text>

      <View style={styles.foot}>
        <Text style={styles.meta}>
          {count} {count === 1 ? "item" : "items"} ·{" "}
          {order.fulfilment_type === "pickup" ? "Collecting" : "Delivery"} · {when(order.created_at)}
        </Text>
        <Text style={styles.total}>{naira(order.total)}</Text>
      </View>

      {order.status === "ready_for_pickup" && order.pickup_code ? (
        <View style={styles.codeRow}>
          <Feather name="key" size={14} color={colors.leaf} />
          <Text style={styles.code}>{order.pickup_code}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

export function StatusPill({ look }: { look: ReturnType<typeof statusLook> }) {
  const palette = {
    waiting: [colors.saffronSoft, colors.saffronInk],
    active: [colors.blueSoft, colors.blue],
    done: [colors.mint, colors.leaf],
    bad: [colors.redSoft, colors.red],
  }[look.tone];
  return (
    <View style={[styles.pill, { backgroundColor: palette[0] }]}>
      <Text style={[styles.pillText, { color: palette[1] }]}>{look.label}</Text>
    </View>
  );
}

/** "Today", "Yesterday", then the date — nobody needs a timestamp on a shopping app. */
export function when(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const sameDay = (a: Date, b: Date) =>
    a.getDate() === b.getDate() && a.getMonth() === b.getMonth() && a.getFullYear() === b.getFullYear();
  if (sameDay(date, today)) {
    return date.toLocaleTimeString("en-NG", { hour: "numeric", minute: "2-digit" });
  }
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (sameDay(date, yesterday)) return "Yesterday";
  return date.toLocaleDateString("en-NG", { day: "numeric", month: "short" });
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.ink, letterSpacing: -0.6 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 16,
    gap: 7,
  },
  head: { flexDirection: "row", alignItems: "center", gap: 10 },
  shop: { flex: 1, fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.ink },
  pill: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999 },
  pillText: { fontFamily: fonts.bodySemibold, fontSize: 12 },
  items: { fontFamily: fonts.body, fontSize: 14, color: colors.muted },
  foot: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
    gap: 10,
    borderTopWidth: 1,
    borderTopColor: colors.line,
    paddingTop: 9,
    marginTop: 2,
  },
  meta: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.muted },
  total: { fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.ink },
  codeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.mint,
    borderRadius: 10,
    paddingVertical: 7,
    paddingHorizontal: 10,
  },
  code: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.forest, letterSpacing: 1.5 },
});
