import { Feather } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button, TextField } from "../components/ui";
import { errorMessage } from "../config/api";
import { useStatusBar } from "../hooks/useStatusBar";
import { Fulfilment, cartService, groupByShop } from "../services/cart";
import { useAuth } from "../store/auth";
import { colors, fonts, naira } from "../theme";

export default function Checkout() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const user = useAuth((s) => s.user);

  const cart = useQuery({ queryKey: ["cart"], queryFn: cartService.get });

  const [choices, setChoices] = useState<Record<string, Fulfilment>>({});
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [touched, setTouched] = useState(false);

  const shops = useMemo(() => (cart.data ? groupByShop(cart.data) : []), [cart.data]);

  // Start each shop on whatever it can actually do, then let the customer change it.
  useEffect(() => {
    if (!shops.length) return;
    setChoices((current) => {
      const next = { ...current };
      let changed = false;
      for (const shop of shops) {
        if (next[shop.businessId]) continue;
        next[shop.businessId] = shop.delivers ? "delivery" : "pickup";
        changed = true;
      }
      return changed ? next : current;
    });
  }, [shops]);

  useEffect(() => {
    if (!name && user?.first_name) setName([user.first_name, user.last_name].filter(Boolean).join(" "));
  }, [user, name]);

  const anyDelivery = shops.some((s) => choices[s.businessId] === "delivery");
  const deliveryTotal = shops.reduce(
    (sum, s) => sum + (choices[s.businessId] === "delivery" ? s.deliveryFee : 0),
    0,
  );
  const itemsTotal = shops.reduce((sum, s) => sum + s.total, 0);
  const grandTotal = itemsTotal + deliveryTotal;

  const missing = anyDelivery && (!name.trim() || !phone.trim() || !address.trim());

  const placeOrder = useMutation({
    mutationFn: () =>
      cartService.checkout({
        fulfilment: choices,
        delivery: anyDelivery
          ? { recipient_name: name.trim(), phone: phone.trim(), address: address.trim() }
          : undefined,
      }),
    onSuccess: (group) => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      router.replace({ pathname: "/order-placed", params: { id: group.id } });
    },
  });

  if (cart.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  if (cart.isError || !cart.data || shops.length === 0) {
    return (
      <View style={[styles.centre, { paddingHorizontal: 20, gap: 14 }]}>
        <Banner tone="danger" icon="shopping-bag">
          {cart.isError ? errorMessage(cart.error) : "Your cart is empty."}
        </Banner>
        <Button title="Back to cart" variant="secondary" onPress={() => router.replace("/cart")} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.sand }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Back"
          onPress={() => router.back()}
          style={styles.back}
        >
          <Feather name="chevron-left" size={22} color={colors.ink} />
        </Pressable>
        <Text style={styles.title}>Checkout</Text>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 28, gap: 18 }}
        keyboardShouldPersistTaps="handled"
      >
        {/* How each shop gets the goods to you */}
        <View style={{ gap: 12 }}>
          <Text style={styles.sectionTitle}>
            {shops.length > 1 ? "How each shop sends your order" : "How you'll get it"}
          </Text>

          {shops.map((shop) => {
            const choice = choices[shop.businessId] ?? "pickup";
            return (
              <View key={shop.businessId} style={styles.shopCard}>
                <View style={styles.shopHead}>
                  <Text style={styles.shopName} numberOfLines={1}>
                    {shop.businessName}
                  </Text>
                  <Text style={styles.shopItems}>
                    {shop.items.length} {shop.items.length === 1 ? "item" : "items"} ·{" "}
                    {naira(shop.total)}
                  </Text>
                </View>

                {shop.delivers ? (
                  <View style={styles.options}>
                    <Option
                      icon="truck"
                      title="Delivery"
                      note={shop.deliveryFee > 0 ? naira(shop.deliveryFee) : "Free"}
                      selected={choice === "delivery"}
                      onPress={() =>
                        setChoices((c) => ({ ...c, [shop.businessId]: "delivery" }))
                      }
                    />
                    <Option
                      icon="shopping-bag"
                      title="I'll collect"
                      note="No fee"
                      selected={choice === "pickup"}
                      onPress={() => setChoices((c) => ({ ...c, [shop.businessId]: "pickup" }))}
                    />
                  </View>
                ) : (
                  <View style={styles.pickupOnly}>
                    <Feather name="shopping-bag" size={15} color={colors.muted} />
                    <Text style={styles.pickupOnlyText}>
                      This shop doesn't deliver — you'll collect from them. They'll give you a
                      code to show.
                    </Text>
                  </View>
                )}
              </View>
            );
          })}
        </View>

        {/* Where it's going */}
        {anyDelivery ? (
          <View style={{ gap: 12 }}>
            <Text style={styles.sectionTitle}>Where should they bring it?</Text>
            <TextField
              label="Name"
              value={name}
              onChangeText={setName}
              placeholder="Who should they ask for?"
              autoCapitalize="words"
              error={touched && !name.trim() ? "Please add a name" : undefined}
            />
            <TextField
              label="Phone number"
              value={phone}
              onChangeText={setPhone}
              placeholder="08030000000"
              keyboardType="phone-pad"
              error={touched && !phone.trim() ? "Please add a phone number" : undefined}
            />
            <TextField
              label="Address"
              value={address}
              onChangeText={setAddress}
              placeholder="Street, house number, and a landmark"
              multiline
              numberOfLines={3}
              style={{ height: 76, textAlignVertical: "top", paddingTop: 12 }}
              error={touched && !address.trim() ? "Please add an address" : undefined}
            />
            <Text style={styles.hint}>
              A landmark helps — most riders in Asaba find you faster by "opposite the filling
              station" than by street number.
            </Text>
          </View>
        ) : null}

        {/* What it costs */}
        <View style={{ gap: 10 }}>
          <Text style={styles.sectionTitle}>What you'll pay</Text>
          <View style={styles.summary}>
            <Row label="Items" value={naira(itemsTotal)} />
            <Row label="Delivery" value={deliveryTotal > 0 ? naira(deliveryTotal) : "—"} />
            {shops.length > 1 && deliveryTotal > 0
              ? shops
                  .filter((s) => choices[s.businessId] === "delivery" && s.deliveryFee > 0)
                  .map((s) => (
                    <Row
                      key={s.businessId}
                      label={`  ${s.businessName}`}
                      value={naira(s.deliveryFee)}
                      small
                    />
                  ))
              : null}
            <View style={styles.rule} />
            <Row label="Total" value={naira(grandTotal)} strong />
          </View>
          {shops.length > 1 ? (
            <Banner tone="info" icon="package">
              You pay once. Each shop prepares and sends its own part, so they may not arrive
              together.
            </Banner>
          ) : null}
        </View>

        {placeOrder.isError ? (
          <Banner tone="danger" icon="alert-circle">{errorMessage(placeOrder.error)}</Banner>
        ) : null}
      </ScrollView>

      <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 14) }]}>
        <Text style={styles.holdNote}>
          Your items are held for 30 minutes once you place the order.
        </Text>
        <Button
          title={`Place order · ${naira(grandTotal)}`}
          loading={placeOrder.isPending}
          onPress={() => {
            setTouched(true);
            if (!missing) placeOrder.mutate();
          }}
        />
      </View>
    </KeyboardAvoidingView>
  );
}

function Option({
  icon,
  title,
  note,
  selected,
  onPress,
}: {
  icon: keyof typeof Feather.glyphMap;
  title: string;
  note: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      accessibilityLabel={`${title}, ${note}`}
      onPress={onPress}
      // A generous tap target: this is a thumb on a phone, not a mouse.
      hitSlop={6}
      style={({ pressed }) => [
        styles.option,
        selected && styles.optionOn,
        pressed && { opacity: 0.7 },
      ]}
    >
      {/* The tick is the thing you actually see change. Colour alone was far too
          faint — mint and sand are nearly the same shade on a phone in daylight,
          which made a working tap look like a dead button. */}
      <View style={[styles.tick, selected && styles.tickOn]}>
        {selected ? <Feather name="check" size={13} color={colors.white} /> : null}
      </View>
      <Feather name={icon} size={17} color={selected ? colors.forest : colors.muted} />
      <Text style={[styles.optionTitle, selected && styles.optionTitleOn]}>{title}</Text>
      <Text style={[styles.optionNote, selected && { color: colors.leaf }]}>{note}</Text>
    </Pressable>
  );
}

function Row({
  label,
  value,
  strong,
  small,
}: {
  label: string;
  value: string;
  strong?: boolean;
  small?: boolean;
}) {
  return (
    <View style={styles.row}>
      <Text
        style={[
          styles.rowLabel,
          strong && { fontFamily: fonts.bodyBold, color: colors.ink },
          small && { fontSize: 12.5 },
        ]}
      >
        {label}
      </Text>
      <Text
        style={[
          styles.rowValue,
          strong && { fontFamily: fonts.displayBold, fontSize: 20 },
          small && { fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.muted },
        ]}
      >
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 20,
    paddingBottom: 14,
  },
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
  title: { fontFamily: fonts.display, fontSize: 26, color: colors.ink, letterSpacing: -0.5 },
  sectionTitle: { fontFamily: fonts.displayBold, fontSize: 17, color: colors.ink },
  shopCard: {
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
    gap: 12,
  },
  shopHead: { gap: 2 },
  shopName: { fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.ink },
  shopItems: { fontFamily: fonts.bodyMedium, fontSize: 13, color: colors.muted },
  options: { flexDirection: "row", gap: 10 },
  option: {
    flex: 1,
    alignItems: "center",
    gap: 3,
    paddingTop: 10,
    paddingBottom: 12,
    paddingHorizontal: 8,
    borderRadius: 14,
    borderWidth: 2,
    borderColor: colors.line,
    backgroundColor: colors.white,
  },
  optionOn: { borderColor: colors.leaf, backgroundColor: colors.mint },
  tick: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 2,
  },
  tickOn: { borderColor: colors.leaf, backgroundColor: colors.leaf },
  optionTitle: { fontFamily: fonts.bodySemibold, fontSize: 14, color: colors.ink },
  optionTitleOn: { fontFamily: fonts.bodyBold, color: colors.forest },
  optionNote: { fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.muted },
  pickupOnly: { flexDirection: "row", gap: 8, alignItems: "flex-start" },
  pickupOnlyText: {
    flex: 1,
    fontFamily: fonts.body,
    fontSize: 13,
    lineHeight: 19,
    color: colors.muted,
  },
  hint: { fontFamily: fonts.body, fontSize: 12.5, lineHeight: 18, color: colors.muted },
  summary: {
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 16,
    gap: 8,
  },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 12 },
  rowLabel: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 14.5, color: colors.muted },
  rowValue: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  rule: { height: 1, backgroundColor: colors.line, marginVertical: 2 },
  bar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.line,
    gap: 8,
  },
  holdNote: { fontFamily: fonts.body, fontSize: 12.5, color: colors.muted, textAlign: "center" },
});
