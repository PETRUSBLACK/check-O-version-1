import { Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { PRODUCT_LOOK } from "../../components/categories";
import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { Cart as CartData, CartItem, cartService, groupByShop, unitCount } from "../../services/cart";
import { colors, fonts, naira } from "../../theme";

export default function Cart() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();

  const cart = useQuery({ queryKey: ["cart"], queryFn: cartService.get });

  const change = useMutation({
    mutationFn: ({ productId, quantity }: { productId: string; quantity: number }) =>
      cartService.setQuantity(productId, quantity),
    onSuccess: (data) => queryClient.setQueryData(["cart"], data),
  });

  const setQuantity = (productId: string, quantity: number) =>
    change.mutate({ productId, quantity });

  if (cart.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  if (cart.isError) {
    return (
      <View style={[styles.page, { paddingTop: insets.top + 20 }]}>
        <Text style={styles.title}>Your cart</Text>
        <View style={{ gap: 12, marginTop: 16 }}>
          <Banner tone="danger" icon="wifi-off">{errorMessage(cart.error)}</Banner>
          <Button title="Try again" variant="secondary" onPress={() => cart.refetch()} />
        </View>
      </View>
    );
  }

  const data: CartData = cart.data;
  const shops = groupByShop(data);
  const units = unitCount(data);

  if (shops.length === 0) {
    return (
      <View style={[styles.page, { paddingTop: insets.top + 20 }]}>
        <Text style={styles.title}>Your cart</Text>
        <EmptyState
          icon="shopping-bag"
          title="Your cart is empty"
          body="Add items from any shop. You'll pay once, and each shop sends its own part."
          action={
            <Button
              title="Start shopping"
              onPress={() => router.navigate("/")}
              style={{ marginTop: 8, alignSelf: "stretch" }}
            />
          }
        />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.sand }}>
      <ScrollView
        contentContainerStyle={{ paddingHorizontal: 20, paddingTop: insets.top + 20, paddingBottom: 24, gap: 16 }}
      >
        <Text style={styles.title}>Your cart</Text>

        {shops.length > 1 ? (
          <Banner tone="info" icon="package">
            {shops.length} shops. You pay once, and each shop delivers its own part separately.
          </Banner>
        ) : null}

        {change.isError ? (
          <Banner tone="danger" icon="alert-circle">{errorMessage(change.error)}</Banner>
        ) : null}

        {shops.map((shop) => (
          <View key={shop.businessId} style={styles.shopBlock}>
            <Pressable
              accessibilityRole="link"
              accessibilityLabel={`Go to ${shop.businessName}`}
              onPress={() =>
                router.push({ pathname: "/shop/[id]", params: { id: shop.businessId, name: shop.businessName } })
              }
              style={styles.shopHead}
            >
              <Feather name="shopping-bag" size={15} color={colors.leaf} />
              <Text style={styles.shopName} numberOfLines={1}>
                {shop.businessName}
              </Text>
              <Feather name="chevron-right" size={17} color={colors.leaf} />
            </Pressable>

            {shop.items.map((item) => (
              <Line
                key={item.id}
                item={item}
                busy={change.isPending}
                onChange={(quantity) => setQuantity(item.product.id, quantity)}
              />
            ))}

            <View style={styles.shopTotal}>
              <Text style={styles.shopTotalLabel}>{shop.businessName} subtotal</Text>
              <Text style={styles.shopTotalValue}>{naira(shop.total)}</Text>
            </View>
          </View>
        ))}
      </ScrollView>

      <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 14) }]}>
        <View style={styles.totalRow}>
          <Text style={styles.totalLabel}>
            Total · {units} {units === 1 ? "item" : "items"}
          </Text>
          <Text style={styles.totalValue}>{naira(data.total)}</Text>
        </View>
        <Text style={styles.deliveryNote}>Delivery is worked out at checkout.</Text>
        <Button title="Checkout coming next" icon="lock" disabled />
      </View>
    </View>
  );
}

function Line({
  item,
  busy,
  onChange,
}: {
  item: CartItem;
  busy: boolean;
  onChange: (quantity: number) => void;
}) {
  const look = PRODUCT_LOOK;
  const max = item.product.available_stock;
  const tooMany = item.quantity > max;

  return (
    <View style={styles.line}>
      <Pressable
        accessibilityRole="link"
        accessibilityLabel={`Open ${item.product.name}`}
        onPress={() => router.push({ pathname: "/product/[id]", params: { id: item.product.id } })}
        style={[styles.thumb, { backgroundColor: look.tint }]}
      >
        {item.product.cover_image ? (
          <Image
            source={{ uri: item.product.cover_image }}
            style={StyleSheet.absoluteFill}
            resizeMode="cover"
            accessibilityIgnoresInvertColors
          />
        ) : (
          <MaterialCommunityIcons name={look.icon} size={24} color={look.ink} />
        )}
      </Pressable>

      <View style={{ flex: 1, gap: 4 }}>
        <Text style={styles.lineName} numberOfLines={2}>
          {item.product.name}
        </Text>
        <Text style={styles.linePrice}>{naira(item.line_total)}</Text>
        {tooMany ? (
          <Text style={styles.warn}>Only {max} left — reduce to continue</Text>
        ) : null}

        <View style={styles.stepper}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={item.quantity === 1 ? "Remove from cart" : "Fewer"}
            disabled={busy}
            onPress={() => onChange(item.quantity - 1)}
            style={({ pressed }) => [styles.step, pressed && { opacity: 0.5 }]}
          >
            <Feather name={item.quantity === 1 ? "trash-2" : "minus"} size={16} color={colors.ink} />
          </Pressable>
          <Text style={styles.quantity} accessibilityLabel={`Quantity ${item.quantity}`}>
            {item.quantity}
          </Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="More"
            disabled={busy || item.quantity >= max}
            onPress={() => onChange(item.quantity + 1)}
            style={({ pressed }) => [
              styles.step,
              (pressed || item.quantity >= max) && { opacity: 0.5 },
            ]}
          >
            <Feather name="plus" size={16} color={colors.ink} />
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  page: { flex: 1, backgroundColor: colors.sand, paddingHorizontal: 20 },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.ink, letterSpacing: -0.6 },
  shopBlock: {
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
    gap: 12,
  },
  shopHead: { flexDirection: "row", alignItems: "center", gap: 7 },
  shopName: { flex: 1, fontFamily: fonts.bodyBold, fontSize: 15, color: colors.leaf },
  line: { flexDirection: "row", gap: 12 },
  thumb: { width: 72, height: 72, borderRadius: 14, alignItems: "center", justifyContent: "center", overflow: "hidden" },
  lineName: { fontFamily: fonts.bodyMedium, fontSize: 14.5, lineHeight: 19, color: colors.ink },
  linePrice: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  warn: { fontFamily: fonts.bodySemibold, fontSize: 12.5, color: colors.red },
  stepper: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 2 },
  step: {
    width: 34,
    height: 34,
    borderRadius: 11,
    backgroundColor: colors.sand,
    borderWidth: 1,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
  },
  quantity: { fontFamily: fonts.bodyBold, fontSize: 16, color: colors.ink, minWidth: 20, textAlign: "center" },
  shopTotal: {
    flexDirection: "row",
    justifyContent: "space-between",
    borderTopWidth: 1,
    borderTopColor: colors.line,
    paddingTop: 10,
  },
  shopTotalLabel: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 13.5, color: colors.muted },
  shopTotalValue: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  bar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.line,
    gap: 8,
  },
  totalRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" },
  totalLabel: { fontFamily: fonts.bodyMedium, fontSize: 14.5, color: colors.muted },
  totalValue: { fontFamily: fonts.displayBold, fontSize: 22, color: colors.ink },
  deliveryNote: { fontFamily: fonts.body, fontSize: 12.5, color: colors.muted, marginTop: -4, marginBottom: 2 },
});
