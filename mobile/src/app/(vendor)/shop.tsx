import { Feather } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { MyShop, statusLook, vendorService } from "../../services/vendor";
import { colors, fonts, naira, radius } from "../../theme";

/**
 * Where a shop owner finds out whether anyone can see them yet.
 *
 * This screen used to say "Check-O is signing shops up one at a time — get in
 * touch and we'll set yours up", which was true when there was no sign-up flow
 * and is a dead end now that there is. What it has to answer is one question:
 * can customers see me, and if not, what is stopping them?
 */
export default function MyShopScreen() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();

  const shops = useQuery({ queryKey: ["my-shops"], queryFn: vendorService.myShops });

  if (shops.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  const mine = shops.data ?? [];

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.sand }}
      contentContainerStyle={{
        paddingHorizontal: 20,
        paddingTop: insets.top + 20,
        paddingBottom: 28,
        gap: 14,
      }}
      refreshControl={
        <RefreshControl
          refreshing={shops.isRefetching}
          onRefresh={() => shops.refetch()}
          tintColor={colors.leaf}
        />
      }
    >
      <Text style={styles.title}>My shop</Text>

      {shops.isError ? (
        <>
          <Banner tone="danger" icon="wifi-off">
            {errorMessage(shops.error)}
          </Banner>
          <Button title="Try again" variant="secondary" onPress={() => shops.refetch()} />
        </>
      ) : mine.length === 0 ? (
        <EmptyState
          icon="home"
          title="No shop yet"
          body="Set your shop up and start selling. It takes a few minutes, and nothing goes live until someone at Check-O has looked it over."
          action={
            <Button
              title="Set up my shop"
              icon="plus"
              onPress={() => router.push("/shop-setup")}
              style={{ marginTop: 14, alignSelf: "stretch" }}
            />
          }
        />
      ) : (
        mine.map((shop) => <ShopCard key={shop.id} shop={shop} />)
      )}

      {mine.length > 0 ? (
        <Banner tone="info" icon="package">
          Your prices, stock and what you set aside for Check-O are on the Products tab.
        </Banner>
      ) : null}
    </ScrollView>
  );
}

function ShopCard({ shop }: { shop: MyShop }) {
  const queryClient = useQueryClient();
  const [sendError, setSendError] = useState<string | null>(null);

  const look = statusLook(shop);
  const outstanding = shop.missing_before_review ?? [];
  const canSend = shop.status === "draft" || shop.status === "rejected";
  const ready = canSend && outstanding.length === 0;

  const send = useMutation({
    mutationFn: () => vendorService.submitForReview(shop.id),
    onSuccess: () => {
      setSendError(null);
      queryClient.invalidateQueries({ queryKey: ["my-shops"] });
    },
    onError: (err) => setSendError(errorMessage(err)),
  });

  const pill = {
    ok: [colors.mint, colors.leaf],
    waiting: [colors.saffronSoft, colors.saffronInk],
    bad: [colors.redSoft, colors.red],
    draft: [colors.blueSoft, colors.blue],
  }[look.tone];

  return (
    <View style={styles.card}>
      <View style={styles.head}>
        <Text style={styles.name} numberOfLines={2}>
          {shop.name}
        </Text>
        <View style={[styles.pill, { backgroundColor: pill[0] }]}>
          <Text style={[styles.pillText, { color: pill[1] }]}>{look.label}</Text>
        </View>
      </View>

      <Text style={[styles.explain, look.tone === "bad" && { color: colors.red }]}>{look.explain}</Text>

      <View style={styles.rule} />

      <Fact icon="tag" text={shop.category_display} />
      {shop.business_phone ? <Fact icon="phone" text={shop.business_phone} /> : null}
      {shop.display_address || shop.address ? (
        <Fact icon="map-pin" text={shop.display_address || shop.address} />
      ) : null}
      <Fact
        icon={shop.delivers ? "truck" : "shopping-bag"}
        text={
          shop.delivers
            ? `You deliver · ${Number(shop.delivery_fee) > 0 ? naira(shop.delivery_fee) : "free"}`
            : "Customers collect from you"
        }
      />

      {/* The checklist. Showing the vendor exactly what is left is the difference
          between "send it in" working and a button that just refuses. */}
      {canSend && outstanding.length > 0 ? (
        <View style={styles.todo}>
          <Text style={styles.todoTitle}>
            {outstanding.length === 1 ? "One thing left" : `${outstanding.length} things left`}
          </Text>
          {outstanding.map((item) => (
            <View key={item} style={styles.todoRow}>
              <Feather name="circle" size={14} color={colors.saffronInk} style={{ marginTop: 2 }} />
              <Text style={styles.todoText}>{item}</Text>
            </View>
          ))}
          {outstanding.some((item) => item.toLowerCase().includes("product")) ? (
            <Pressable
              accessibilityRole="button"
              onPress={() => router.push("/(vendor)/products")}
              hitSlop={6}
            >
              <Text style={styles.link}>Add a product →</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}

      {sendError ? (
        <Banner tone="danger" icon="alert-circle">
          {sendError}
        </Banner>
      ) : null}

      <View style={styles.actions}>
        {ready ? (
          <Button
            title={shop.status === "rejected" ? "Send it in again" : "Send my shop in"}
            icon="send"
            loading={send.isPending}
            onPress={() => send.mutate()}
          />
        ) : null}

        <Button
          title={canSend ? "Edit my shop details" : "Edit my shop"}
          variant="secondary"
          icon="edit-2"
          onPress={() => router.push({ pathname: "/shop-setup", params: { id: shop.id } })}
        />
      </View>
    </View>
  );
}

function Fact({ icon, text }: { icon: keyof typeof Feather.glyphMap; text: string }) {
  return (
    <View style={styles.fact}>
      <Feather name={icon} size={15} color={colors.muted} />
      <Text style={styles.factText}>{text}</Text>
    </View>
  );
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
    gap: 9,
  },
  head: { gap: 8 },
  name: { fontFamily: fonts.displayBold, fontSize: 19, color: colors.ink, letterSpacing: -0.3 },
  pill: { alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999 },
  pillText: { fontFamily: fonts.bodySemibold, fontSize: 12 },
  explain: { fontFamily: fonts.body, fontSize: 13.5, lineHeight: 20, color: colors.muted },
  rule: { height: 1, backgroundColor: colors.line, marginVertical: 3 },
  fact: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  factText: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 13.5, lineHeight: 19, color: colors.muted },

  todo: {
    backgroundColor: colors.saffronSoft,
    borderRadius: radius.sm,
    padding: 13,
    gap: 7,
    marginTop: 4,
  },
  todoTitle: { fontFamily: fonts.bodyBold, fontSize: 13.5, color: colors.saffronInk },
  todoRow: { flexDirection: "row", gap: 8 },
  todoText: {
    flex: 1,
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    lineHeight: 19,
    color: colors.saffronInk,
  },
  link: {
    fontFamily: fonts.bodyBold,
    fontSize: 13,
    color: colors.leaf,
    marginTop: 2,
  },

  actions: { gap: 9, marginTop: 5 },
});
