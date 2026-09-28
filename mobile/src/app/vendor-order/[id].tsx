import { Feather } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
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

import { StatusPill, when } from "../(tabs)/orders";
import { Banner, Button, EmptyState, TextField } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { ordersService, statusLook } from "../../services/orders";
import {
  CANCEL_REASONS,
  VendorCancelReason,
  nextAction,
  vendorCanCancel,
  vendorService,
} from "../../services/vendor";
import { colors, fonts, naira } from "../../theme";

export default function VendorOrderDetail() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [code, setCode] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [reason, setReason] = useState<VendorCancelReason | null>(null);
  const [note, setNote] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  const order = useQuery({ queryKey: ["order", id], queryFn: () => ordersService.get(id) });

  const refresh = (updated: Awaited<ReturnType<typeof ordersService.get>>) => {
    queryClient.setQueryData(["order", id], updated);
    queryClient.invalidateQueries({ queryKey: ["vendor-orders"] });
    setProblem(null);
  };

  const act = useMutation({
    mutationFn: async (run: NonNullable<ReturnType<typeof nextAction>>["run"]) => {
      if (run === "ready") return vendorService.markReady(id);
      if (run === "collected") return vendorService.confirmCollected(id, code);
      return vendorService.advance(id, run);
    },
    onSuccess: (updated) => {
      refresh(updated);
      setCode("");
    },
    onError: (e) => setProblem(errorMessage(e)),
  });

  const cancel = useMutation({
    mutationFn: () => vendorService.cancel(id, reason!, note.trim()),
    onSuccess: (updated) => {
      refresh(updated);
      setCancelling(false);
      setReason(null);
      setNote("");
    },
    onError: (e) => setProblem(errorMessage(e)),
  });

  if (order.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  if (order.isError) {
    return (
      <View style={[styles.centre, { paddingHorizontal: 20, gap: 14 }]}>
        <EmptyState icon="alert-circle" title="Couldn't open this order" body={errorMessage(order.error)} />
        <Button title="Back" variant="secondary" onPress={() => router.replace("/(vendor)")} />
      </View>
    );
  }

  const data = order.data;
  const look = statusLook(data);
  const action = nextAction(data);
  const collecting = data.fulfilment_type === "pickup";
  const needsCode = action?.run === "collected";
  const canAct = action && (!needsCode || code.trim().length >= 4);

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.sand }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Back"
          onPress={() => (router.canGoBack() ? router.back() : router.replace("/(vendor)"))}
          style={styles.back}
        >
          <Feather name="chevron-left" size={22} color={colors.ink} />
        </Pressable>
        <Text style={styles.title}>#{data.id.slice(0, 8).toUpperCase()}</Text>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 28, gap: 14 }}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.card}>
          <View style={styles.statusRow}>
            <StatusPill look={look} />
            <Text style={styles.placed}>Ordered {when(data.created_at)}</Text>
          </View>
          <View style={styles.way}>
            <Feather name={collecting ? "shopping-bag" : "truck"} size={15} color={colors.leaf} />
            <Text style={styles.wayText}>
              {collecting ? "Customer is collecting this" : "You are delivering this"}
            </Text>
          </View>
        </View>

        {/* What to pack */}
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Pack this</Text>
          {data.items.map((item) => (
            <View key={item.id} style={styles.line}>
              <Text style={styles.qty}>{item.quantity}×</Text>
              <Text style={styles.itemName} numberOfLines={2}>
                {item.product_name}
              </Text>
              <Text style={styles.itemPrice}>{naira(Number(item.unit_price) * item.quantity)}</Text>
            </View>
          ))}
          <View style={styles.rule} />
          <Row label="Goods" value={naira(data.items_total)} />
          {Number(data.delivery_fee) > 0 ? (
            <Row label="Delivery you charged" value={naira(data.delivery_fee)} />
          ) : null}
          <Row label="Order total" value={naira(data.total)} strong />
        </View>

        {/* Where it goes */}
        {!collecting && data.delivery_address ? (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Deliver to</Text>
            <Text style={styles.address}>{data.delivery_address}</Text>
            <Text style={styles.recipient}>
              {data.recipient_name}
              {data.delivery_phone ? ` · ${data.delivery_phone}` : ""}
            </Text>
          </View>
        ) : null}

        {problem ? <Banner tone="danger" icon="alert-circle">{problem}</Banner> : null}

        {/* Confirming collection needs the customer's code */}
        {needsCode ? (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Ask for their code</Text>
            <Text style={styles.codeHelp}>
              The customer has a code on their phone. Type it here before you hand the goods over.
            </Text>
            <TextField
              label="Collection code"
              value={code}
              onChangeText={setCode}
              placeholder="SM-0000"
              autoCapitalize="characters"
            />
          </View>
        ) : null}

        {/* Cancelling — a shop has to say why */}
        {cancelling ? (
          <View style={styles.cancelCard}>
            <Text style={styles.cancelTitle}>Why are you cancelling?</Text>
            <Text style={styles.cancelBody}>
              The customer is told, and the goods go back into your stock.
              {data.paid_at ? " They'll be refunded." : ""}
            </Text>
            {CANCEL_REASONS.map((r) => (
              <Pressable
                key={r.value}
                accessibilityRole="radio"
                accessibilityState={{ selected: reason === r.value }}
                onPress={() => setReason(r.value)}
                style={[styles.reason, reason === r.value && styles.reasonOn]}
              >
                <Feather
                  name={reason === r.value ? "check-circle" : "circle"}
                  size={18}
                  color={reason === r.value ? colors.red : colors.muted}
                />
                <Text style={styles.reasonText}>{r.label}</Text>
              </Pressable>
            ))}
            {reason === "other" ? (
              <TextField
                label="Tell the customer what happened"
                value={note}
                onChangeText={setNote}
                placeholder="A short explanation"
                multiline
                style={{ height: 66, textAlignVertical: "top", paddingTop: 12 }}
              />
            ) : null}
            <View style={{ flexDirection: "row", gap: 10 }}>
              <Button
                title="Keep it"
                variant="secondary"
                style={{ flex: 1 }}
                onPress={() => {
                  setCancelling(false);
                  setProblem(null);
                }}
              />
              <Button
                title="Cancel order"
                variant="danger"
                style={{ flex: 1 }}
                loading={cancel.isPending}
                disabled={!reason || (reason === "other" && !note.trim())}
                onPress={() => cancel.mutate()}
              />
            </View>
          </View>
        ) : null}
      </ScrollView>

      {action || (vendorCanCancel(data) && !cancelling) ? (
        <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 14) }]}>
          {action ? (
            <>
              {action.hint ? <Text style={styles.hint}>{action.hint}</Text> : null}
              <Button
                title={action.label}
                loading={act.isPending}
                disabled={!canAct}
                onPress={() => act.mutate(action.run)}
              />
            </>
          ) : null}
          {vendorCanCancel(data) && !cancelling ? (
            <Pressable
              accessibilityRole="button"
              onPress={() => setCancelling(true)}
              hitSlop={8}
              style={{ paddingVertical: 4 }}
            >
              <Text style={styles.cancelLink}>I can't fulfil this order</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}
    </KeyboardAvoidingView>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <View style={styles.row}>
      <Text style={[styles.rowLabel, strong && { fontFamily: fonts.bodyBold, color: colors.ink }]}>
        {label}
      </Text>
      <Text style={[styles.rowValue, strong && { fontFamily: fonts.displayBold, fontSize: 19 }]}>
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
  title: {
    flex: 1,
    fontFamily: fonts.display,
    fontSize: 22,
    color: colors.ink,
    letterSpacing: 0.5,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 16,
    gap: 9,
  },
  statusRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  placed: { fontFamily: fonts.bodyMedium, fontSize: 12.5, color: colors.muted },
  way: { flexDirection: "row", alignItems: "center", gap: 7 },
  wayText: { fontFamily: fonts.bodySemibold, fontSize: 13.5, color: colors.leaf },
  sectionTitle: { fontFamily: fonts.displayBold, fontSize: 16.5, color: colors.ink },
  line: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  qty: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.leaf, minWidth: 28 },
  itemName: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 14.5, lineHeight: 20, color: colors.ink },
  itemPrice: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  rule: { height: 1, backgroundColor: colors.line, marginVertical: 3 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 12 },
  rowLabel: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 14, color: colors.muted },
  rowValue: { fontFamily: fonts.bodyBold, fontSize: 14.5, color: colors.ink },
  address: { fontFamily: fonts.body, fontSize: 14.5, lineHeight: 21, color: colors.ink },
  recipient: { fontFamily: fonts.bodyMedium, fontSize: 13.5, color: colors.muted },
  codeHelp: { fontFamily: fonts.body, fontSize: 13.5, lineHeight: 19, color: colors.muted },
  cancelCard: {
    backgroundColor: colors.redSoft,
    borderRadius: 18,
    padding: 16,
    gap: 10,
  },
  cancelTitle: { fontFamily: fonts.bodyBold, fontSize: 15.5, color: colors.red },
  cancelBody: { fontFamily: fonts.body, fontSize: 13.5, lineHeight: 19, color: colors.red },
  reason: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: colors.white,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: "transparent",
    paddingVertical: 12,
    paddingHorizontal: 12,
  },
  reasonOn: { borderColor: colors.red },
  reasonText: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 14, color: colors.ink },
  bar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.line,
    gap: 8,
    alignItems: "stretch",
  },
  hint: { fontFamily: fonts.body, fontSize: 12.5, color: colors.muted, textAlign: "center" },
  cancelLink: {
    fontFamily: fonts.bodySemibold,
    fontSize: 13.5,
    color: colors.red,
    textAlign: "center",
  },
});
