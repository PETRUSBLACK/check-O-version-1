import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { VendorProduct, shelfNote, vendorService } from "../../services/vendor";
import { colors, fonts, naira } from "../../theme";

export default function VendorProducts() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const [query, setQuery] = useState("");

  const shops = useQuery({ queryKey: ["my-shops"], queryFn: vendorService.myShops });
  const shop = shops.data?.[0];

  const products = useQuery({
    queryKey: ["vendor-products", shop?.id],
    queryFn: () => vendorService.products(shop!.id),
    enabled: !!shop,
  });

  const visible = useMemo(() => {
    const all = products.data ?? [];
    const q = query.trim().toLowerCase();
    const matched = q ? all.filter((p) => p.name.toLowerCase().includes(q)) : all;
    // What needs attention first: sold out, then running low, then the rest.
    return [...matched].sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));
  }, [products.data, query]);

  const soldOut = (products.data ?? []).filter(
    (p) => p.is_active && p.available_stock <= 0,
  ).length;

  if (shops.isPending || (shop && products.isPending)) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  if (!shop) {
    return (
      <View style={[styles.page, { paddingTop: insets.top + 20 }]}>
        <Text style={styles.title}>My products</Text>
        <EmptyState
          icon="home"
          title="No shop yet"
          body="Your products live here once you have a shop. Set it up first — it takes a few minutes."
          action={
            <Button
              title="Set up my shop"
              icon="plus"
              onPress={() => router.push("/shop-setup")}
              style={{ marginTop: 14, alignSelf: "stretch" }}
            />
          }
        />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.sand }}>
      <FlatList
        data={visible}
        keyExtractor={(p) => p.id}
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 24, gap: 10 }}
        refreshControl={
          <RefreshControl
            refreshing={products.isRefetching}
            onRefresh={() => products.refetch()}
            tintColor={colors.leaf}
          />
        }
        ListHeaderComponent={
          <View style={{ gap: 12, paddingTop: insets.top + 20, paddingBottom: 4 }}>
            <Text style={styles.title}>My products</Text>

            {soldOut > 0 ? (
              <Banner tone="warning" icon="alert-circle">
                {soldOut === 1
                  ? "1 product is sold out. Customers can't order it until you add stock."
                  : `${soldOut} products are sold out. Customers can't order them until you add stock.`}
              </Banner>
            ) : null}

            {(products.data ?? []).length > 6 ? (
              <View style={styles.search}>
                <Feather name="search" size={18} color={colors.muted} />
                <TextInput
                  accessibilityLabel="Search your products"
                  placeholder="Search your products"
                  placeholderTextColor="#8A938E"
                  value={query}
                  onChangeText={setQuery}
                  style={styles.searchInput}
                />
              </View>
            ) : null}

            {products.isError ? (
              <>
                <Banner tone="danger" icon="wifi-off">{errorMessage(products.error)}</Banner>
                <Button title="Try again" variant="secondary" onPress={() => products.refetch()} />
              </>
            ) : null}
          </View>
        }
        ListEmptyComponent={
          products.isError ? null : query ? (
            <EmptyState
              icon="search"
              title="Nothing matched"
              body={`You have no product called "${query}".`}
            />
          ) : (
            <EmptyState
              icon="package"
              title="No products yet"
              body="Add what you sell and it shows up for customers near you."
            />
          )
        }
        renderItem={({ item }) => <ProductRow product={item} />}
      />

      <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 14) }]}>
        <Button
          title="Add a product"
          icon="plus"
          onPress={() => router.push({ pathname: "/vendor-product/new", params: { shop: shop.id } })}
        />
      </View>
    </View>
  );
}

function rank(product: VendorProduct): number {
  if (!product.is_active) return 3;
  if (product.available_stock <= 0) return 0;
  if (product.available_stock <= 5) return 1;
  return 2;
}

function ProductRow({ product }: { product: VendorProduct }) {
  const note = shelfNote(product);
  const palette = {
    ok: [colors.mint, colors.leaf],
    low: [colors.saffronSoft, colors.saffronInk],
    out: [colors.redSoft, colors.red],
    hidden: ["#ECEAE3", colors.muted],
  }[note.tone];

  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`${product.name}, ${naira(product.price)}, ${note.text}`}
      onPress={() => router.push({ pathname: "/vendor-product/[id]", params: { id: product.id } })}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.9 }]}
    >
      {/* A thumbnail here turns "no photo" from something invisible into a visible
          gap in the shop's own list, which is the only thing that gets it fixed. */}
      {product.cover_image ? (
        <Image source={{ uri: product.cover_image }} style={styles.thumb} resizeMode="cover" />
      ) : (
        <View style={[styles.thumb, styles.thumbEmpty]}>
          <Feather name="camera" size={16} color={colors.muted} />
          <Text style={styles.thumbEmptyText}>No photo</Text>
        </View>
      )}

      <View style={{ flex: 1, gap: 3 }}>
        <Text style={styles.name} numberOfLines={2}>
          {product.name}
        </Text>
        <Text style={styles.price}>{naira(product.price)}</Text>
        {product.uses_channel_allocation && product.is_active ? (
          <Text style={styles.split}>
            {product.smartmall_allocation} of {product.stock} set aside for Check-O
          </Text>
        ) : null}
      </View>

      <View style={{ alignItems: "flex-end", gap: 6 }}>
        <View style={[styles.pill, { backgroundColor: palette[0] }]}>
          <Text style={[styles.pillText, { color: palette[1] }]}>{note.text}</Text>
        </View>
        <Feather name="chevron-right" size={18} color={colors.muted} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  page: { flex: 1, backgroundColor: colors.sand, paddingHorizontal: 20 },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.ink, letterSpacing: -0.6 },
  search: {
    height: 48,
    borderRadius: 14,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.line,
    paddingHorizontal: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  searchInput: { flex: 1, fontFamily: fonts.body, fontSize: 15, color: colors.ink, paddingVertical: 0 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: colors.white,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
  },
  thumb: { width: 54, height: 54, borderRadius: 12, backgroundColor: colors.mint },
  thumbEmpty: {
    alignItems: "center",
    justifyContent: "center",
    gap: 1,
    backgroundColor: "#F1EFE8",
    borderWidth: 1,
    borderColor: colors.line,
    borderStyle: "dashed",
  },
  thumbEmptyText: { fontFamily: fonts.bodyMedium, fontSize: 8.5, color: colors.muted },
  name: { fontFamily: fonts.bodyBold, fontSize: 15, lineHeight: 20, color: colors.ink },
  price: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  split: { fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.muted },
  pill: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999 },
  pillText: { fontFamily: fonts.bodySemibold, fontSize: 12 },
  bar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.line,
  },
});
