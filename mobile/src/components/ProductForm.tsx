import { Feather } from "@expo/vector-icons";
import { ReactNode, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ProductChanges, VendorProduct } from "../services/vendor";
import { colors, fonts, naira } from "../theme";
import { Banner, Button, TextField } from "./ui";

export interface ProductFormValues {
  name: string;
  price: string;
  stock: string;
  /** "" means Check-O may sell everything in the shop. */
  allocation: string;
  /** Warn the shop when available stock falls to this. "" means use the default. */
  lowStockAt: string;
  description: string;
  isActive: boolean;
}

export function initialValues(product?: VendorProduct): ProductFormValues {
  return {
    name: product?.name ?? "",
    price: product ? String(Number(product.price)) : "",
    stock: product ? String(product.stock) : "",
    allocation:
      product?.smartmall_allocation === null || product?.smartmall_allocation === undefined
        ? ""
        : String(product.smartmall_allocation),
    lowStockAt: product ? String(product.low_stock_threshold) : "",
    description: product?.description ?? "",
    isActive: product?.is_active ?? true,
  };
}

/** Turns what was typed into what the API wants, or lists what's wrong. */
export function toChanges(v: ProductFormValues): { changes: ProductChanges } | { errors: Errors } {
  const errors: Errors = {};
  const name = v.name.trim();
  if (!name) errors.name = "Give it a name";

  const price = Number(v.price.replace(/[^0-9.]/g, ""));
  if (!v.price.trim()) errors.price = "Give it a price";
  else if (!Number.isFinite(price) || price <= 0) errors.price = "Price must be a number above zero";

  const stock = Number(v.stock.replace(/[^0-9]/g, ""));
  if (!v.stock.trim()) errors.stock = "Say how many you have";
  else if (!Number.isFinite(stock) || stock < 0) errors.stock = "That isn't a number";

  const setsAside = v.allocation.trim() !== "";
  const allocation = Number(v.allocation.replace(/[^0-9]/g, ""));
  if (setsAside) {
    if (!Number.isFinite(allocation) || allocation < 0) errors.allocation = "That isn't a number";
    else if (allocation > stock) errors.allocation = `You only have ${stock} in the shop`;
  }

  const warnAt = v.lowStockAt.trim();
  const lowStockThreshold = Number(warnAt.replace(/[^0-9]/g, ""));
  if (warnAt && (!Number.isFinite(lowStockThreshold) || lowStockThreshold < 0)) {
    errors.lowStockAt = "That isn't a number";
  }

  if (Object.keys(errors).length) return { errors };
  return {
    changes: {
      name,
      price: price.toFixed(2),
      stock,
      smartmall_allocation: setsAside ? allocation : null,
      description: v.description.trim(),
      is_active: v.isActive,
      // Left blank, the backend keeps its own default rather than being sent 0,
      // which would mean "only warn me once it has completely finished".
      ...(warnAt ? { low_stock_threshold: lowStockThreshold } : {}),
    },
  };
}

type Errors = Partial<Record<keyof ProductFormValues | "allocation" | "lowStockAt", string>>;

export function ProductForm({
  title,
  values,
  onChange,
  onSubmit,
  submitLabel,
  saving,
  problem,
  errors,
  existing,
  photos,
  onBack,
}: {
  title: string;
  values: ProductFormValues;
  onChange: (next: ProductFormValues) => void;
  onSubmit: () => void;
  submitLabel: string;
  saving: boolean;
  problem: string | null;
  errors: Errors;
  existing?: boolean;
  /** The photo strip. Only on an existing product — a photo needs something to belong to. */
  photos?: ReactNode;
  onBack: () => void;
}) {
  const insets = useSafeAreaInsets();
  const [showDescription, setShowDescription] = useState(!!values.description);
  const set = (patch: Partial<ProductFormValues>) => onChange({ ...values, ...patch });

  const stock = Number(values.stock.replace(/[^0-9]/g, "")) || 0;
  const setsAside = values.allocation.trim() !== "";
  const allocation = Number(values.allocation.replace(/[^0-9]/g, "")) || 0;

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.sand }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Pressable accessibilityRole="button" accessibilityLabel="Back" onPress={onBack} style={styles.back}>
          <Feather name="chevron-left" size={22} color={colors.ink} />
        </Pressable>
        <Text style={styles.title} numberOfLines={1}>
          {title}
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 28, gap: 14 }}
        keyboardShouldPersistTaps="handled"
      >
        <TextField
          label="What is it?"
          value={values.name}
          onChangeText={(name) => set({ name })}
          placeholder="Rice 50kg bag"
          error={errors.name}
        />

        {/* High up on purpose: the photo is the first thing a shopper sees, so it
            shouldn't be buried under the numbers. */}
        {photos ? (
          <>
            {photos}
            <View style={styles.rule} />
          </>
        ) : null}

        <TextField
          label="Price (₦)"
          value={values.price}
          onChangeText={(price) => set({ price })}
          placeholder="78000"
          keyboardType="numeric"
          error={errors.price}
        />

        <TextField
          label="How many are in your shop?"
          value={values.stock}
          onChangeText={(s) => set({ stock: s })}
          placeholder="40"
          keyboardType="number-pad"
          error={errors.stock}
        />

        {/* The Check-O basket — the thing shop owners find hardest to picture. */}
        <View style={styles.allocationCard}>
          <Text style={styles.sectionTitle}>How many can Check-O sell?</Text>
          <Text style={styles.sectionBody}>
            Customers walking into your shop buy from the same pile. Set some aside so an online
            order never takes the last one from someone standing at your counter.
          </Text>

          <Choice
            label="All of them"
            note="Check-O can sell everything you have"
            selected={!setsAside}
            onPress={() => set({ allocation: "" })}
          />
          <Choice
            label="Only some"
            note="Keep the rest for people who come to the shop"
            selected={setsAside}
            onPress={() => set({ allocation: values.allocation || String(Math.ceil(stock / 3)) })}
          />

          {setsAside ? (
            <>
              <TextField
                label="Set aside for Check-O"
                value={values.allocation}
                onChangeText={(a) => set({ allocation: a })}
                placeholder="12"
                keyboardType="number-pad"
                error={errors.allocation}
              />
              {!errors.allocation && stock > 0 ? (
                <Text style={styles.maths}>
                  {allocation} on Check-O · {Math.max(0, stock - allocation)} for your shop
                </Text>
              ) : null}
            </>
          ) : null}
        </View>

        {/* The shop sets this, not us. Five is nearly empty for sachet water and
            plenty for generators, so a single default can only ever be wrong for
            most products. */}
        <TextField
          label="Warn me when only this many are left"
          value={values.lowStockAt}
          onChangeText={(lowStockAt) => set({ lowStockAt })}
          placeholder="5"
          keyboardType="number-pad"
          error={errors.lowStockAt}
        />
        <Text style={styles.hint}>
          Check-O will tell you once, so you can restock before it finishes. Leave it
          blank to keep the usual five.
        </Text>

        {showDescription ? (
          <TextField
            label="Anything a customer should know (optional)"
            value={values.description}
            onChangeText={(description) => set({ description })}
            placeholder="Long grain parboiled rice, sealed bag."
            multiline
            style={{ height: 76, textAlignVertical: "top", paddingTop: 12 }}
          />
        ) : (
          <Pressable accessibilityRole="button" onPress={() => setShowDescription(true)} hitSlop={8}>
            <Text style={styles.addNote}>+ Add a description</Text>
          </Pressable>
        )}

        {existing ? (
          <Pressable
            accessibilityRole="switch"
            accessibilityState={{ checked: values.isActive }}
            onPress={() => set({ isActive: !values.isActive })}
            style={styles.toggleRow}
          >
            <Feather
              name={values.isActive ? "check-square" : "square"}
              size={22}
              color={values.isActive ? colors.leaf : colors.muted}
            />
            <View style={{ flex: 1 }}>
              <Text style={styles.toggleLabel}>Show this on Check-O</Text>
              <Text style={styles.toggleNote}>
                {values.isActive
                  ? "Customers near you can find and order it."
                  : "Hidden from customers. Nothing is deleted — turn it back on any time."}
              </Text>
            </View>
          </Pressable>
        ) : null}

        {problem ? <Banner tone="danger" icon="alert-circle">{problem}</Banner> : null}
      </ScrollView>

      <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 14) }]}>
        <Button title={submitLabel} loading={saving} onPress={onSubmit} />
      </View>
    </KeyboardAvoidingView>
  );
}

function Choice({
  label,
  note,
  selected,
  onPress,
}: {
  label: string;
  note: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      accessibilityLabel={`${label}. ${note}`}
      onPress={onPress}
      style={[styles.choice, selected && styles.choiceOn]}
    >
      <Feather
        name={selected ? "check-circle" : "circle"}
        size={19}
        color={selected ? colors.leaf : colors.muted}
      />
      <View style={{ flex: 1 }}>
        <Text style={[styles.choiceLabel, selected && { color: colors.leaf }]}>{label}</Text>
        <Text style={styles.choiceNote}>{note}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  rule: { height: 1, backgroundColor: colors.line, marginVertical: 2 },
  hint: { fontFamily: fonts.body, fontSize: 12.5, lineHeight: 18, color: colors.muted, marginTop: -6 },
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
  title: { flex: 1, fontFamily: fonts.display, fontSize: 23, color: colors.ink, letterSpacing: -0.5 },
  allocationCard: {
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 16,
    gap: 10,
  },
  sectionTitle: { fontFamily: fonts.displayBold, fontSize: 16.5, color: colors.ink },
  sectionBody: { fontFamily: fonts.body, fontSize: 13.5, lineHeight: 19.5, color: colors.muted },
  choice: {
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
    backgroundColor: colors.sand,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: "transparent",
    padding: 13,
  },
  choiceOn: { borderColor: colors.leaf, backgroundColor: colors.mint },
  choiceLabel: { fontFamily: fonts.bodySemibold, fontSize: 14.5, color: colors.ink },
  choiceNote: { fontFamily: fonts.body, fontSize: 12.5, lineHeight: 17, color: colors.muted },
  maths: {
    fontFamily: fonts.bodySemibold,
    fontSize: 13,
    color: colors.leaf,
    textAlign: "center",
    marginTop: -2,
  },
  addNote: { fontFamily: fonts.bodySemibold, fontSize: 14, color: colors.leaf, paddingVertical: 4 },
  toggleRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 11,
    backgroundColor: colors.white,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
  },
  toggleLabel: { fontFamily: fonts.bodySemibold, fontSize: 14.5, color: colors.ink },
  toggleNote: { fontFamily: fonts.body, fontSize: 12.5, lineHeight: 17.5, color: colors.muted, marginTop: 2 },
  bar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.line,
  },
});
