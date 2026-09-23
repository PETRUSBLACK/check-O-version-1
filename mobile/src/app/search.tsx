import { Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, FlatList, Image, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { stockNote } from "../components/ProductCard";
import { Banner, EmptyState } from "../components/ui";
import { errorMessage } from "../config/api";
import { useStatusBar } from "../hooks/useStatusBar";
import { productsService } from "../services/products";
import { colors, fonts, naira } from "../theme";

export default function Search() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ q?: string }>();
  const [text, setText] = useState(params.q ?? "");
  const [q, setQ] = useState(params.q ?? "");

  const results = useQuery({
    queryKey: ["search", q],
    queryFn: () => productsService.list({ search: q }),
    enabled: q.length > 0,
  });

  return (
    <View style={[styles.page, { paddingTop: insets.top + 12 }]}>
      <View style={styles.bar}>
        <Pressable accessibilityRole="button" accessibilityLabel="Back" onPress={() => router.back()} style={styles.back}>
          <Feather name="chevron-left" size={22} color={colors.ink} />
        </Pressable>
        <View style={styles.search}>
          <Feather name="search" size={19} color={colors.muted} />
          <TextInput
            accessibilityLabel="Search products"
            value={text}
            onChangeText={setText}
            onSubmitEditing={() => setQ(text.trim())}
            returnKeyType="search"
            autoFocus={!params.q}
            placeholder="Search products"
            placeholderTextColor="#8A938E"
            style={styles.input}
          />
        </View>
      </View>

      {!q ? null : results.isPending ? (
        <ActivityIndicator color={colors.leaf} style={{ marginTop: 40 }} />
      ) : results.isError ? (
        <Banner tone="danger" icon="wifi-off">{errorMessage(results.error)}</Banner>
      ) : results.data.length === 0 ? (
        <EmptyState icon="search" title={`No results for "${q}"`} body="Try a shorter or different word." />
      ) : (
        <FlatList
          data={results.data}
          keyExtractor={(p) => p.id}
          contentContainerStyle={{ paddingBottom: insets.bottom + 24 }}
          ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: colors.line }} />}
          ListHeaderComponent={
            <Text style={styles.count}>
              {results.data.length} result{results.data.length === 1 ? "" : "s"}
            </Text>
          }
          renderItem={({ item }) => {
            const stock = stockNote(item.available_stock);
            return (
              <Pressable
                accessibilityRole="link"
                accessibilityLabel={`${item.name}, ${naira(item.price)}, at ${item.business_name}`}
                onPress={() => router.push({ pathname: "/product/[id]", params: { id: item.id } })}
                style={({ pressed }) => [styles.row, pressed && { opacity: 0.8 }]}
              >
                <View style={styles.thumb}>
                  {item.cover_image ? (
                    <Image
                      source={{ uri: item.cover_image }}
                      style={StyleSheet.absoluteFill}
                      resizeMode="cover"
                      accessibilityIgnoresInvertColors
                    />
                  ) : (
                    <MaterialCommunityIcons name="package-variant-closed" size={26} color={colors.leaf} />
                  )}
                </View>
                <View style={{ flex: 1, gap: 3 }}>
                  <Text style={styles.name} numberOfLines={2}>
                    {item.name}
                  </Text>
                  <Text style={styles.shop} numberOfLines={1}>
                    {item.business_name}
                  </Text>
                  <Text style={styles.price}>{naira(item.price)}</Text>
                  <Text style={[styles.stock, stock.tone !== "ok" && { color: colors.red }]}>{stock.text}</Text>
                </View>
                <Feather name="chevron-right" size={18} color={colors.muted} />
              </Pressable>
            );
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.sand, paddingHorizontal: 20, gap: 12 },
  bar: { flexDirection: "row", alignItems: "center", gap: 10 },
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
  search: {
    flex: 1,
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
  input: { flex: 1, fontFamily: fonts.body, fontSize: 15, color: colors.ink, paddingVertical: 0 },
  count: { fontFamily: fonts.bodySemibold, fontSize: 13, color: colors.muted, marginBottom: 6 },
  row: { flexDirection: "row", gap: 14, alignItems: "center", paddingVertical: 12 },
  thumb: {
    width: 64,
    height: 64,
    borderRadius: 14,
    backgroundColor: colors.mint,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  name: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  shop: { fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.leaf },
  price: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  stock: { fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.muted },
});
