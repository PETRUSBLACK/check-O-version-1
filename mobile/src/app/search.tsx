import { Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, Image, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { stockNote } from "../components/ProductCard";
import { Banner, EmptyState } from "../components/ui";
import { errorMessage } from "../config/api";
import { useStatusBar } from "../hooks/useStatusBar";
import { productsService } from "../services/products";
import { colors, fonts, naira } from "../theme";

/**
 * How long to wait after the last keystroke before asking the server.
 *
 * Not zero: searching on every letter would send a request per keystroke, and in
 * Asaba the customer pays for that data. 350ms is long enough that typing
 * "groundnut" is one search rather than nine, and short enough to feel immediate.
 */
const PAUSE_MS = 350;

/** One letter matches almost everything, which is a slow way to learn nothing. */
const MIN_LETTERS = 2;

export default function Search() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ q?: string }>();
  const [text, setText] = useState(params.q ?? "");
  const [q, setQ] = useState(params.q ?? "");

  // Search as they type, once they stop for a moment.
  useEffect(() => {
    const trimmed = text.trim();
    if (trimmed === q) return;
    const timer = setTimeout(() => setQ(trimmed), PAUSE_MS);
    return () => clearTimeout(timer);
  }, [text, q]);

  const results = useQuery({
    queryKey: ["search", q],
    queryFn: () => productsService.list({ search: q }),
    enabled: q.length >= MIN_LETTERS,
    // Keep the previous results on screen while the next ones load. Without this
    // the list empties on every new letter, which reads as "nothing found".
    placeholderData: keepPreviousData,
  });

  const searching = q.length >= MIN_LETTERS && results.isFetching;
  const tooShort = text.trim().length > 0 && text.trim().length < MIN_LETTERS;

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
            // Pressing search skips the wait rather than doing nothing.
            onSubmitEditing={() => setQ(text.trim())}
            returnKeyType="search"
            autoFocus={!params.q}
            autoCorrect={false}
            placeholder="Search products"
            placeholderTextColor="#8A938E"
            style={styles.input}
          />
          {/* A small spinner in the box, so results can stay on screen while the
              next ones load instead of the list blinking out. */}
          {searching ? (
            <ActivityIndicator size="small" color={colors.muted} />
          ) : text.length > 0 ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Clear search"
              hitSlop={8}
              onPress={() => {
                setText("");
                setQ("");
              }}
            >
              <Feather name="x" size={18} color={colors.muted} />
            </Pressable>
          ) : null}
        </View>
      </View>

      {tooShort ? (
        <Text style={styles.hint}>Keep typing — two letters or more.</Text>
      ) : !q ? null : results.isPending ? (
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
  hint: { fontFamily: fonts.body, fontSize: 13.5, color: colors.muted, marginTop: 6 },
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
