import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { MyShop, vendorService } from "../../services/vendor";
import { colors, fonts, naira } from "../../theme";

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

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.sand }}
      contentContainerStyle={{ paddingHorizontal: 20, paddingTop: insets.top + 20, paddingBottom: 28, gap: 14 }}
      refreshControl={
        <RefreshControl refreshing={shops.isRefetching} onRefresh={() => shops.refetch()} tintColor={colors.leaf} />
      }
    >
      <Text style={styles.title}>My shop</Text>

      {shops.isError ? (
        <>
          <Banner tone="danger" icon="wifi-off">{errorMessage(shops.error)}</Banner>
          <Button title="Try again" variant="secondary" onPress={() => shops.refetch()} />
        </>
      ) : (shops.data ?? []).length === 0 ? (
        <EmptyState
          icon="home"
          title="No shop yet"
          body="Check-O is signing shops up one at a time for now. Get in touch and we'll set yours up, and you'll see it here."
        />
      ) : (
        (shops.data ?? []).map((shop) => <ShopCard key={shop.id} shop={shop} />)
      )}

      <Banner tone="info" icon="package">
        Your prices, stock and what you set aside for Check-O are on the Products tab.
      </Banner>
    </ScrollView>
  );
}

function ShopCard({ shop }: { shop: MyShop }) {
  const approved = shop.status === "approved";
  return (
    <View style={styles.card}>
      <View style={styles.head}>
        <Text style={styles.name} numberOfLines={2}>
          {shop.name}
        </Text>
        <View style={[styles.pill, { backgroundColor: approved ? colors.mint : colors.saffronSoft }]}>
          <Text style={[styles.pillText, { color: approved ? colors.leaf : colors.saffronInk }]}>
            {approved ? "Open on Check-O" : "Waiting for approval"}
          </Text>
        </View>
      </View>

      <Fact icon="tag" text={shop.category_display} />
      {shop.address ? <Fact icon="map-pin" text={shop.address} /> : null}
      <Fact
        icon={shop.delivers ? "truck" : "shopping-bag"}
        text={
          shop.delivers
            ? `You deliver · ${Number(shop.delivery_fee) > 0 ? naira(shop.delivery_fee) : "free"}`
            : "Customers collect from you"
        }
      />

      {!approved ? (
        <Text style={styles.pending}>
          Your shop won't show up for customers until it's approved.
        </Text>
      ) : null}
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
  fact: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  factText: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 13.5, lineHeight: 19, color: colors.muted },
  pending: {
    fontFamily: fonts.body,
    fontSize: 13,
    lineHeight: 19,
    color: colors.saffronInk,
    marginTop: 2,
  },
});
