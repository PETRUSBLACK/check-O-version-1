import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { StatusPill, when } from "../(tabs)/orders";
import { NotificationBell } from "../../components/NotificationBell";
import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { Order, ordersService, statusLook } from "../../services/orders";
import { useAuth } from "../../store/auth";
import { needsAction, nextAction, statusLook as shopStatusLook, vendorService } from "../../services/vendor";
import { colors, fonts, naira } from "../../theme";

type Filter = "todo" | "all";

export default function VendorOrders() {
  useStatusBar("light");
  const insets = useSafeAreaInsets();
  const user = useAuth((s) => s.user);
  const [filter, setFilter] = useState<Filter>("todo");

  const orders = useQuery({ queryKey: ["vendor-orders"], queryFn: ordersService.list });

  // A seller with no shop, or a shop nobody can see yet, will never get an order
  // and should not be left staring at an empty list wondering why. This is the
  // first screen the seller app opens on, so the nudge belongs here.
  const shops = useQuery({ queryKey: ["my-shops"], queryFn: vendorService.myShops });
  const firstShop = shops.data?.[0];
  const notSellingYet = shops.isSuccess && (!firstShop || firstShop.status !== "approved");

  // Only orders this shop has to fulfil — a seller may also have bought things.
  const mine = useMemo(
    () => (orders.data ?? []).filter((o) => o.customer !== user?.id),
    [orders.data, user],
  );
  const todo = useMemo(() => mine.filter(needsAction), [mine]);
  const shown = filter === "todo" ? todo : mine;

  const money = todo.reduce((sum, o) => sum + Number(o.total), 0);

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
      data={shown}
      keyExtractor={(o) => o.id}
      contentContainerStyle={{ paddingBottom: 24, gap: 12 }}
      refreshControl={
        <RefreshControl
          refreshing={orders.isRefetching}
          onRefresh={() => orders.refetch()}
          tintColor={colors.leaf}
        />
      }
      ListHeaderComponent={
        <View>
          <View style={[styles.header, { paddingTop: insets.top + 16 }]}>
            <View style={styles.headerRow}>
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={styles.hello}>
                  {todo.length === 0
                    ? "Nothing waiting"
                    : `${todo.length} order${todo.length === 1 ? "" : "s"} to sort out`}
                </Text>
                {todo.length > 0 ? (
                  <Text style={styles.worth}>{naira(money)} waiting to be fulfilled</Text>
                ) : (
                  <Text style={styles.worth}>You're all caught up.</Text>
                )}
              </View>
              <NotificationBell onDark />
            </View>
          </View>

          <View style={styles.tabs}>
            <Toggle label="To do" count={todo.length} on={filter === "todo"} onPress={() => setFilter("todo")} />
            <Toggle label="All orders" count={mine.length} on={filter === "all"} onPress={() => setFilter("all")} />
          </View>

          {notSellingYet ? (
            <View style={{ paddingHorizontal: 20, gap: 10, paddingBottom: 4 }}>
              <Banner tone="warning" icon="home">
                {!firstShop
                  ? "You haven't set your shop up yet, so customers can't find you."
                  : shopStatusLook(firstShop).explain}
              </Banner>
              <Button
                title={!firstShop ? "Set up my shop" : "Go to my shop"}
                icon={!firstShop ? "plus" : "arrow-right"}
                onPress={() =>
                  router.push(!firstShop ? "/shop-setup" : "/(vendor)/shop")
                }
              />
            </View>
          ) : null}

          {orders.isError ? (
            <View style={{ paddingHorizontal: 20, gap: 12 }}>
              <Banner tone="danger" icon="wifi-off">{errorMessage(orders.error)}</Banner>
              <Button title="Try again" variant="secondary" onPress={() => orders.refetch()} />
            </View>
          ) : null}
        </View>
      }
      ListEmptyComponent={
        orders.isError ? null : filter === "todo" ? (
          <EmptyState
            icon="check-circle"
            title="Nothing to do"
            body="When a customer orders from your shop, it lands here."
            action={
              mine.length > 0 ? (
                <Button
                  title="See all orders"
                  variant="secondary"
                  onPress={() => setFilter("all")}
                  style={{ marginTop: 8, alignSelf: "stretch" }}
                />
              ) : undefined
            }
          />
        ) : (
          <EmptyState
            icon="inbox"
            title="No orders yet"
            body="Your shop hasn't had an order through Check-O yet."
          />
        )
      }
      renderItem={({ item }) => <VendorOrderRow order={item} />}
    />
  );
}

function Toggle({
  label,
  count,
  on,
  onPress,
}: {
  label: string;
  count: number;
  on: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: on }}
      onPress={onPress}
      style={[styles.toggle, on && styles.toggleOn]}
    >
      <Text style={[styles.toggleText, on && { color: colors.white }]}>
        {label} ({count})
      </Text>
    </Pressable>
  );
}

function VendorOrderRow({ order }: { order: Order }) {
  const look = statusLook(order);
  const action = nextAction(order);
  const units = order.items.reduce((total, i) => total + i.quantity, 0);

  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`Order, ${look.label}, ${naira(order.total)}`}
      onPress={() => router.push({ pathname: "/vendor-order/[id]", params: { id: order.id } })}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.9 }]}
    >
      <View style={styles.cardHead}>
        <Text style={styles.reference}>#{order.id.slice(0, 8).toUpperCase()}</Text>
        <StatusPill look={look} />
      </View>

      {order.items.slice(0, 3).map((item) => (
        <Text key={item.id} style={styles.item} numberOfLines={1}>
          {item.quantity}× {item.product_name}
        </Text>
      ))}
      {order.items.length > 3 ? (
        <Text style={styles.more}>and {order.items.length - 3} more</Text>
      ) : null}

      <View style={styles.cardFoot}>
        <View style={styles.way}>
          <Feather
            name={order.fulfilment_type === "pickup" ? "shopping-bag" : "truck"}
            size={14}
            color={colors.muted}
          />
          <Text style={styles.wayText}>
            {order.fulfilment_type === "pickup" ? "Collecting" : "Delivery"} · {units}{" "}
            {units === 1 ? "item" : "items"} · {when(order.created_at)}
          </Text>
        </View>
        <Text style={styles.total}>{naira(order.total)}</Text>
      </View>

      {action ? (
        <View style={styles.next}>
          <Feather name="arrow-right-circle" size={15} color={colors.leaf} />
          <Text style={styles.nextText}>{action.label}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  header: {
    backgroundColor: colors.forest,
    paddingHorizontal: 20,
    paddingBottom: 22,
    gap: 4,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  headerRow: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  hello: { fontFamily: fonts.display, fontSize: 26, color: colors.white, letterSpacing: -0.6 },
  worth: { fontFamily: fonts.bodyMedium, fontSize: 14, color: colors.leafSoft },
  tabs: { flexDirection: "row", gap: 10, paddingHorizontal: 20, paddingTop: 16, paddingBottom: 4 },
  toggle: {
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.white,
  },
  toggleOn: { backgroundColor: colors.leaf, borderColor: colors.leaf },
  toggleText: { fontFamily: fonts.bodySemibold, fontSize: 13.5, color: colors.ink },
  card: {
    marginHorizontal: 20,
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 16,
    gap: 5,
  },
  cardHead: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    marginBottom: 3,
  },
  reference: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.muted, letterSpacing: 0.5 },
  item: { fontFamily: fonts.bodyMedium, fontSize: 14.5, color: colors.ink },
  more: { fontFamily: fonts.body, fontSize: 13, color: colors.muted },
  cardFoot: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
    gap: 10,
    borderTopWidth: 1,
    borderTopColor: colors.line,
    paddingTop: 9,
    marginTop: 5,
  },
  way: { flex: 1, flexDirection: "row", alignItems: "center", gap: 6 },
  wayText: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.muted },
  total: { fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.ink },
  next: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.mint,
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 10,
    marginTop: 4,
  },
  nextText: { fontFamily: fonts.bodySemibold, fontSize: 13.5, color: colors.leaf },
});
