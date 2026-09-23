import { Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { categoryStyle } from "../../components/categories";
import { ProductCard } from "../../components/ProductCard";
import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { productsService } from "../../services/products";
import { shopsService } from "../../services/shops";
import { colors, fonts } from "../../theme";

export default function ShopScreen() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const { id, name, category } = useLocalSearchParams<{ id: string; name?: string; category?: string }>();
  const [query, setQuery] = useState("");

  const shop = useQuery({
    queryKey: ["shop", id],
    queryFn: () => shopsService.get(id),
  });

  const products = useQuery({
    queryKey: ["shop-products", id],
    queryFn: () => productsService.list({ business: id }),
  });

  // The card that got us here already knows the name and category, so the page
  // has a title immediately instead of flashing a spinner.
  const shopName = shop.data?.name ?? name ?? "Shop";
  const shopCategory = shop.data?.category ?? category ?? "";
  const look = categoryStyle(shopCategory);

  const visible = useMemo(() => {
    const all = products.data ?? [];
    const q = query.trim().toLowerCase();
    if (!q) return all;
    return all.filter((p) => p.name.toLowerCase().includes(q));
  }, [products.data, query]);

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.sand }}
      data={visible}
      keyExtractor={(p) => p.id}
      numColumns={2}
      columnWrapperStyle={{ gap: 12, paddingHorizontal: 20 }}
      contentContainerStyle={{ gap: 12, paddingBottom: 32 }}
      renderItem={({ item }) => <ProductCard product={item} shopCategory={shopCategory} />}
      ListHeaderComponent={
        <View>
          <View style={[styles.cover, { backgroundColor: look.tint, paddingTop: insets.top }]}>
            {shop.data?.cover_image ? (
              <Image
                source={{ uri: shop.data.cover_image }}
                style={StyleSheet.absoluteFill}
                resizeMode="cover"
                accessibilityIgnoresInvertColors
              />
            ) : (
              <MaterialCommunityIcons name={look.icon} size={64} color={look.ink} />
            )}
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Back"
              onPress={() => router.back()}
              style={[styles.back, { top: insets.top + 12 }]}
            >
              <Feather name="chevron-left" size={22} color={colors.ink} />
            </Pressable>
          </View>

          <View style={styles.sheet}>
            <Text style={styles.name}>{shopName}</Text>
            <View style={styles.metaRow}>
              <Text style={styles.meta}>{look.label}</Text>
              {shop.data?.avg_rating ? (
                <>
                  <Text style={styles.dot}>·</Text>
                  <Feather name="star" size={14} color={colors.saffron} />
                  <Text style={styles.meta}>
                    {shop.data.avg_rating.toFixed(1)} ({shop.data.rating_count})
                  </Text>
                </>
              ) : null}
            </View>
            {shop.data?.address ? (
              <View style={styles.addressRow}>
                <Feather name="map-pin" size={14} color={colors.muted} />
                <Text style={styles.address} numberOfLines={2}>
                  {shop.data.address}
                </Text>
              </View>
            ) : null}

            {(products.data?.length ?? 0) > 6 ? (
              <View style={styles.search}>
                <Feather name="search" size={18} color={colors.muted} />
                <TextInput
                  accessibilityLabel={`Search in ${shopName}`}
                  placeholder={`Search in ${shopName}`}
                  placeholderTextColor="#8A938E"
                  value={query}
                  onChangeText={setQuery}
                  returnKeyType="search"
                  style={styles.searchInput}
                />
              </View>
            ) : null}

            <Text style={styles.sectionTitle}>
              {query ? `Results for "${query}"` : "What they sell"}
            </Text>
          </View>
        </View>
      }
      ListEmptyComponent={
        products.isPending ? (
          <ActivityIndicator color={colors.leaf} style={{ marginVertical: 40 }} />
        ) : products.isError ? (
          <View style={{ paddingHorizontal: 20, gap: 12 }}>
            <Banner tone="danger" icon="wifi-off">{errorMessage(products.error)}</Banner>
            <Button title="Try again" variant="secondary" onPress={() => products.refetch()} />
          </View>
        ) : query ? (
          <EmptyState
            icon="search"
            title="Nothing matched"
            body={`This shop has no product called "${query}". Try a shorter word.`}
          />
        ) : (
          <EmptyState
            icon="package"
            title="Nothing listed yet"
            body="This shop hasn't put any products on Check-O yet. Check back soon."
          />
        )
      }
    />
  );
}

const styles = StyleSheet.create({
  cover: { height: 200, alignItems: "center", justifyContent: "center" },
  back: {
    position: "absolute",
    left: 16,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
  },
  sheet: {
    marginTop: -24,
    backgroundColor: colors.sand,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: 20,
    paddingTop: 20,
    gap: 10,
  },
  name: { fontFamily: fonts.display, fontSize: 26, color: colors.ink, letterSpacing: -0.5 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: -4 },
  meta: { fontFamily: fonts.bodyMedium, fontSize: 14, color: colors.muted },
  dot: { color: colors.muted, fontSize: 14 },
  addressRow: { flexDirection: "row", alignItems: "flex-start", gap: 6 },
  address: { flex: 1, fontFamily: fonts.body, fontSize: 13.5, lineHeight: 19, color: colors.muted },
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
    marginTop: 4,
  },
  searchInput: { flex: 1, fontFamily: fonts.body, fontSize: 15, color: colors.ink, paddingVertical: 0 },
  sectionTitle: {
    fontFamily: fonts.displayBold,
    fontSize: 18,
    color: colors.ink,
    marginTop: 6,
    marginBottom: 2,
  },
});
