import { Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { PRODUCT_LOOK } from "../../components/categories";
import { stockNote } from "../../components/ProductCard";
import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { cartService } from "../../services/cart";
import { productsService } from "../../services/products";
import { colors, fonts, naira } from "../../theme";

export default function ProductScreen() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  const product = useQuery({
    queryKey: ["product", id],
    queryFn: () => productsService.get(id),
  });

  const addToCart = useMutation({
    mutationFn: () => cartService.add(id, quantity),
    onSuccess: (cart) => {
      queryClient.setQueryData(["cart"], cart);
      setAdded(true);
    },
  });

  if (product.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  if (product.isError) {
    return (
      <View style={[styles.centre, { paddingHorizontal: 20, gap: 14 }]}>
        <EmptyState icon="alert-circle" title="Couldn't open this product" body={errorMessage(product.error)} />
        <Button title="Try again" variant="secondary" onPress={() => product.refetch()} />
        <Button title="Go back" variant="secondary" onPress={() => router.back()} />
      </View>
    );
  }

  const item = product.data;
  const look = PRODUCT_LOOK;
  const stock = stockNote(item.available_stock);
  const soldOut = stock.tone === "out";
  const atMax = quantity >= item.available_stock;
  const lineTotal = Number(item.price) * quantity;

  return (
    <View style={{ flex: 1, backgroundColor: colors.sand }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
        <View style={[styles.photo, { backgroundColor: look.tint, paddingTop: insets.top }]}>
          {item.cover_image ? (
            <Image
              source={{ uri: item.cover_image }}
              style={StyleSheet.absoluteFill}
              resizeMode="cover"
              accessibilityIgnoresInvertColors
            />
          ) : (
            <MaterialCommunityIcons name={look.icon} size={72} color={look.ink} />
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
          <Pressable
            accessibilityRole="link"
            accessibilityLabel={`Go to ${item.business_name}`}
            onPress={() =>
              router.push({ pathname: "/shop/[id]", params: { id: item.business, name: item.business_name } })
            }
            style={styles.shopRow}
          >
            <Feather name="shopping-bag" size={14} color={colors.leaf} />
            <Text style={styles.shopName}>{item.business_name}</Text>
            <Feather name="chevron-right" size={16} color={colors.leaf} />
          </Pressable>

          <Text style={styles.name}>{item.name}</Text>
          <Text style={styles.price}>{naira(item.price)}</Text>

          <View style={[styles.stockPill, stockStyle(stock.tone)]}>
            <Feather
              name={soldOut ? "x-circle" : stock.tone === "low" ? "alert-circle" : "check-circle"}
              size={14}
              color={stockInk(stock.tone)}
            />
            <Text style={[styles.stockText, { color: stockInk(stock.tone) }]}>{stock.text}</Text>
          </View>

          {item.description ? (
            <>
              <Text style={styles.sectionTitle}>About this item</Text>
              <Text style={styles.description}>{item.description}</Text>
            </>
          ) : null}

          {!soldOut ? (
            <>
              <Text style={styles.sectionTitle}>How many?</Text>
              <View style={styles.stepper}>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Fewer"
                  disabled={quantity <= 1}
                  onPress={() => {
                    setAdded(false);
                    setQuantity((q) => Math.max(1, q - 1));
                  }}
                  style={({ pressed }) => [
                    styles.stepButton,
                    (quantity <= 1 || pressed) && { opacity: 0.5 },
                  ]}
                >
                  <Feather name="minus" size={20} color={colors.ink} />
                </Pressable>
                <Text style={styles.quantity} accessibilityLabel={`Quantity ${quantity}`}>
                  {quantity}
                </Text>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="More"
                  disabled={atMax}
                  onPress={() => {
                    setAdded(false);
                    setQuantity((q) => q + 1);
                  }}
                  style={({ pressed }) => [styles.stepButton, (atMax || pressed) && { opacity: 0.5 }]}
                >
                  <Feather name="plus" size={20} color={colors.ink} />
                </Pressable>
                {atMax ? (
                  <Text style={styles.atMax}>That's all this shop has on Check-O</Text>
                ) : null}
              </View>
            </>
          ) : null}

          {addToCart.isError ? (
            <Banner tone="danger" icon="alert-circle">{errorMessage(addToCart.error)}</Banner>
          ) : null}
        </View>
      </ScrollView>

      {/* Add to cart stays on screen while you scroll. */}
      <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 14) }]}>
        {soldOut ? (
          <Button title="Sold out" disabled />
        ) : added ? (
          <View style={{ gap: 8 }}>
            <View style={styles.addedRow}>
              <Feather name="check-circle" size={16} color={colors.leaf} />
              <Text style={styles.addedText}>
                Added {quantity} to your cart
              </Text>
            </View>
            <View style={{ flexDirection: "row", gap: 10 }}>
              <Button
                title="Add another"
                variant="secondary"
                style={{ flex: 1 }}
                loading={addToCart.isPending}
                onPress={() => addToCart.mutate()}
              />
              <Button title="View cart" style={{ flex: 1 }} onPress={() => router.push("/cart")} />
            </View>
          </View>
        ) : (
          <Button
            title={`Add to cart · ${naira(lineTotal)}`}
            icon="shopping-bag"
            loading={addToCart.isPending}
            onPress={() => addToCart.mutate()}
          />
        )}
      </View>
    </View>
  );
}

function stockStyle(tone: "ok" | "low" | "out") {
  if (tone === "out") return { backgroundColor: colors.redSoft };
  if (tone === "low") return { backgroundColor: colors.saffronSoft };
  return { backgroundColor: colors.mint };
}

function stockInk(tone: "ok" | "low" | "out") {
  if (tone === "out") return colors.red;
  if (tone === "low") return colors.saffronInk;
  return colors.leaf;
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  photo: { height: 300, alignItems: "center", justifyContent: "center" },
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
    gap: 8,
  },
  shopRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  shopName: { fontFamily: fonts.bodySemibold, fontSize: 14, color: colors.leaf },
  name: { fontFamily: fonts.display, fontSize: 25, lineHeight: 31, color: colors.ink, letterSpacing: -0.5 },
  price: { fontFamily: fonts.displayBold, fontSize: 24, color: colors.ink },
  stockPill: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    marginTop: 2,
  },
  stockText: { fontFamily: fonts.bodySemibold, fontSize: 13 },
  sectionTitle: { fontFamily: fonts.displayBold, fontSize: 17, color: colors.ink, marginTop: 14 },
  description: { fontFamily: fonts.body, fontSize: 15, lineHeight: 23, color: colors.muted },
  stepper: { flexDirection: "row", alignItems: "center", gap: 14, marginTop: 2 },
  stepButton: {
    width: 46,
    height: 46,
    borderRadius: 14,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
  },
  quantity: { fontFamily: fonts.bodyBold, fontSize: 19, color: colors.ink, minWidth: 28, textAlign: "center" },
  atMax: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.muted },
  addedRow: { flexDirection: "row", alignItems: "center", gap: 7, justifyContent: "center" },
  addedText: { fontFamily: fonts.bodySemibold, fontSize: 13.5, color: colors.leaf },
  bar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.line,
  },
});
