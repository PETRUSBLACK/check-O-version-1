import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import { Product } from "../services/products";
import { colors, fonts, naira } from "../theme";
import { categoryStyle } from "./categories";

/** Words for how many are left — a number alone reads as stock-keeping, not shopping. */
export function stockNote(available: number): { text: string; tone: "ok" | "low" | "out" } {
  if (available <= 0) return { text: "Sold out", tone: "out" };
  if (available <= 5) return { text: `Only ${available} left`, tone: "low" };
  return { text: "In stock", tone: "ok" };
}

export function ProductCard({ product, shopCategory }: { product: Product; shopCategory?: string }) {
  const look = categoryStyle(shopCategory ?? "");
  const stock = stockNote(product.available_stock);
  const soldOut = stock.tone === "out";

  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`${product.name}, ${naira(product.price)}, ${stock.text}`}
      onPress={() => router.push({ pathname: "/product/[id]", params: { id: product.id } })}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.9 }]}
    >
      <View style={[styles.photo, { backgroundColor: look.tint }]}>
        {product.cover_image ? (
          <Image
            source={{ uri: product.cover_image }}
            style={StyleSheet.absoluteFill}
            resizeMode="cover"
            accessibilityIgnoresInvertColors
          />
        ) : (
          <MaterialCommunityIcons name={look.icon} size={34} color={look.ink} />
        )}
        {soldOut ? (
          <View style={styles.soldOut}>
            <Text style={styles.soldOutText}>Sold out</Text>
          </View>
        ) : null}
      </View>
      <View style={styles.body}>
        <Text style={styles.name} numberOfLines={2}>
          {product.name}
        </Text>
        <Text style={styles.price}>{naira(product.price)}</Text>
        {!soldOut && stock.tone === "low" ? <Text style={styles.low}>{stock.text}</Text> : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.line,
    overflow: "hidden",
  },
  photo: { height: 118, alignItems: "center", justifyContent: "center" },
  soldOut: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: "rgba(22,32,28,0.45)",
    alignItems: "center",
    justifyContent: "center",
  },
  soldOutText: {
    fontFamily: fonts.bodyBold,
    fontSize: 13,
    color: colors.white,
    backgroundColor: "rgba(0,0,0,0.35)",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    overflow: "hidden",
  },
  body: { paddingHorizontal: 12, paddingTop: 10, paddingBottom: 12, gap: 3 },
  name: { fontFamily: fonts.bodyMedium, fontSize: 14, lineHeight: 19, color: colors.ink },
  price: { fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.ink },
  low: { fontFamily: fonts.bodySemibold, fontSize: 12, color: colors.saffronInk },
});
