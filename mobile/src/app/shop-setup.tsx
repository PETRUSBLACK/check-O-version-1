import { Feather } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
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
import { findPlaceFromAddress, readCurrentPlace } from "../hooks/useUserLocation";
import { ShopPlace, vendorService } from "../services/vendor";
import { colors, fonts, radius } from "../theme";

/**
 * Setting a shop up, and editing it afterwards.
 *
 * This is the screen that was missing: the app has always told people "after
 * signing up you'll add your shop details", and there was nowhere to do it.
 *
 * Two things it deliberately does NOT do. It does not ask for a CAC number or a
 * tax identifier — a trader in Ogbeogonogo market has neither, and asking would
 * end Check-O's vendor list at about three shops. And it does not submit the
 * shop for review on save. A shop goes in as a draft the vendor can keep
 * working on; sending it in is a separate, deliberate tap on My shop, once they
 * have added some products.
 */

// What Check-O sells, in the vendor's words rather than the database's. The
// values are BusinessCategory on the backend.
const WHAT_YOU_SELL: { value: string; label: string; icon: keyof typeof Feather.glyphMap }[] = [
  { value: "supermarket", label: "Foodstuff & groceries", icon: "shopping-cart" },
  { value: "pharmacy", label: "Pharmacy & drugs", icon: "plus-square" },
  { value: "restaurant", label: "Cooked food", icon: "coffee" },
  { value: "electronics", label: "Phones & electronics", icon: "smartphone" },
  { value: "fashion", label: "Clothes & shoes", icon: "tag" },
  { value: "beauty", label: "Beauty & hair", icon: "scissors" },
  { value: "health", label: "Health & fitness", icon: "activity" },
  { value: "retail", label: "A bit of everything", icon: "package" },
];

export default function ShopSetup() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const { id } = useLocalSearchParams<{ id?: string }>();
  const editing = !!id;

  const shops = useQuery({
    queryKey: ["my-shops"],
    queryFn: vendorService.myShops,
    enabled: editing,
  });
  const shop = (shops.data ?? []).find((s) => s.id === id);

  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [tagline, setTagline] = useState("");
  const [delivers, setDelivers] = useState(false);
  const [fee, setFee] = useState("");
  const [place, setPlace] = useState<ShopPlace | null>(null);
  const [placeLabel, setPlaceLabel] = useState("");
  const [locating, setLocating] = useState(false);
  const [finding, setFinding] = useState(false);
  const [locateNote, setLocateNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fill the form in from the shop being edited, once it arrives.
  useEffect(() => {
    if (!shop) return;
    setName(shop.name);
    setCategory(shop.category);
    setPhone(shop.business_phone ?? "");
    setAddress(shop.address || shop.display_address || "");
    setTagline(shop.tagline ?? "");
    setDelivers(shop.delivers);
    setFee(Number(shop.delivery_fee) > 0 ? String(Math.round(Number(shop.delivery_fee))) : "");
    if (shop.latitude != null && shop.longitude != null) {
      setPlaceLabel("Already pinned on the map");
    }
  }, [shop?.id]);

  // Approval fixes what a shop was approved *as*, so those two stop being
  // editable here rather than failing at the server with a validation error.
  const identityLocked = shop?.status === "approved";

  /**
   * Both buttons answer the same question — where is this shop? — and both end
   * up in the same place. Two routes exist because a shop owner filling this in
   * at home cannot use her phone's position, and one filling it in at her
   * counter should not have to type her street name.
   */
  const pinFound = (found: { lat: number; lng: number; city: string; state: string; label: string }) => {
    setPlace({
      latitude: found.lat,
      longitude: found.lng,
      city: found.city || "Asaba",
      state: found.state || "Delta",
      full_address: found.label || address.trim(),
    });
    setPlaceLabel(found.label || `${found.lat.toFixed(4)}, ${found.lng.toFixed(4)}`);
    // Only fill the address box if it's empty — never overwrite what she typed.
    if (!address.trim() && found.label) setAddress(found.label);
  };

  const useMyLocation = async () => {
    setLocating(true);
    setLocateNote(null);
    const found = await readCurrentPlace();
    setLocating(false);

    if (!found) {
      setLocateNote(
        "Couldn't read your position. Turn location on for Check-O, or type your address above and tap \"Find my address\".",
      );
      return;
    }
    pinFound(found);
  };

  const findFromAddress = async () => {
    if (address.trim().length < 5) {
      setLocateNote("Type your shop's address first, then tap this.");
      return;
    }
    setFinding(true);
    setLocateNote(null);
    const found = await findPlaceFromAddress(address);
    setFinding(false);

    if (!found) {
      setLocateNote(
        "Couldn't find that address on the map. Try adding the town — for example \"12 Nnebisi Road, Asaba\" — or tap \"Use my location\" while you are at the shop.",
      );
      return;
    }
    pinFound(found);
  };

  const save = useMutation({
    mutationFn: async () => {
      const changes = {
        business_phone: phone.trim(),
        address: address.trim(),
        tagline: tagline.trim(),
        delivers,
        // A shop that doesn't deliver has no fee, whatever is left in the box.
        delivery_fee: delivers && fee.trim() ? fee.trim() : "0",
      };

      let shopId: string;
      if (editing) {
        // PATCH echoes the changed fields and not the id, so keep the one we have.
        await vendorService.updateShop(
          id!,
          identityLocked ? changes : { ...changes, name: name.trim(), category },
        );
        shopId = id!;
      } else {
        const created = await vendorService.createShop({
          ...changes,
          name: name.trim(),
          category,
        });
        shopId = created.id;
      }

      // The pin is a separate endpoint, and a shop is still usable without it,
      // so a failure here must not throw away everything else they just typed.
      if (place) {
        try {
          await vendorService.setPlace(shopId, {
            ...place,
            full_address: place.full_address || address.trim(),
          });
        } catch {
          // Silent: My shop will keep listing the map pin as outstanding.
        }
      }
      return shopId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-shops"] });
      router.replace("/(vendor)/shop");
    },
    onError: (err) => setError(errorMessage(err)),
  });

  // A shop that is already pinned does not have to be pinned again every time
  // its owner edits her phone number.
  const alreadyPinned = shop?.latitude != null && shop?.longitude != null;
  const hasPin = place !== null || alreadyPinned;

  const submit = () => {
    setError(null);
    if (!name.trim()) return setError("What is your shop called?");
    if (!category) return setError("Pick what you sell, so customers can find you.");
    if (!phone.trim()) return setError("Customers need a number they can call you on.");
    if (!address.trim()) return setError("Where is your shop? Type the address.");
    if (!hasPin) {
      // Checked here rather than left to the checklist on My shop. Finding out
      // two screens later that the app still does not know where your shop is,
      // after you typed the address, reads as the app not listening.
      return setError(
        "Check-O also needs your shop on the map — that is how customers nearby find you. Tap \"Find my address\" or \"Use my location\".",
      );
    }
    if (delivers && !fee.trim()) {
      return setError("How much do you charge to deliver? Put 0 if it's free.");
    }
    save.mutate();
  };

  if (editing && shops.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView
        style={{ flex: 1, backgroundColor: colors.sand }}
        contentContainerStyle={{
          paddingHorizontal: 20,
          paddingTop: insets.top + 12,
          paddingBottom: 40,
          gap: 16,
        }}
        keyboardShouldPersistTaps="handled"
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Back"
          onPress={() => router.back()}
          hitSlop={8}
          style={styles.back}
        >
          <Feather name="chevron-left" size={22} color={colors.ink} />
        </Pressable>

        <Text style={styles.title}>{editing ? "Your shop" : "Set up your shop"}</Text>
        <Text style={styles.lead}>
          {editing
            ? "Change anything here and customers see it straight away."
            : "This is what customers see when they find you. Nothing goes live until someone at Check-O has looked it over."}
        </Text>

        {error ? (
          <Banner tone="danger" icon="alert-circle">
            {error}
          </Banner>
        ) : null}

        <TextField
          label="What is your shop called?"
          value={name}
          onChangeText={setName}
          placeholder="Mama Ngozi Provisions"
          editable={!identityLocked}
          autoCapitalize="words"
        />

        <View style={{ gap: 8 }}>
          <Text style={styles.label}>What do you sell?</Text>
          <View style={styles.chips} accessibilityRole="radiogroup">
            {WHAT_YOU_SELL.map((option) => {
              const on = category === option.value;
              return (
                <Pressable
                  key={option.value}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: on, disabled: identityLocked }}
                  disabled={identityLocked}
                  onPress={() => setCategory(option.value)}
                  style={[styles.chip, on && styles.chipOn, identityLocked && { opacity: 0.55 }]}
                >
                  <Feather name={option.icon} size={15} color={on ? colors.leaf : colors.muted} />
                  <Text style={[styles.chipText, on && styles.chipTextOn]}>{option.label}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        {identityLocked ? (
          <Text style={styles.hint}>
            Your shop name and what you sell were checked when it was approved, so they can't be changed
            here. Get in touch if either is wrong.
          </Text>
        ) : null}

        <TextField
          label="Phone customers can call"
          value={phone}
          onChangeText={setPhone}
          placeholder="0803 123 4567"
          keyboardType="phone-pad"
        />

        <TextField
          label="Where is your shop?"
          value={address}
          onChangeText={setAddress}
          placeholder="12 Nnebisi Road, Asaba"
          multiline
        />

        <View style={styles.locateRow}>
          <Pressable
            accessibilityRole="button"
            onPress={findFromAddress}
            disabled={finding || locating}
            style={[styles.locate, (finding || locating) && { opacity: 0.6 }]}
          >
            {finding ? (
              <ActivityIndicator size="small" color={colors.leaf} />
            ) : (
              <Feather name="search" size={16} color={colors.leaf} />
            )}
            <Text style={styles.locateText}>{finding ? "Looking…" : "Find my address"}</Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            onPress={useMyLocation}
            disabled={locating || finding}
            style={[styles.locate, (locating || finding) && { opacity: 0.6 }]}
          >
            {locating ? (
              <ActivityIndicator size="small" color={colors.leaf} />
            ) : (
              <Feather name="map-pin" size={16} color={colors.leaf} />
            )}
            <Text style={styles.locateText}>{locating ? "Finding you…" : "Use my location"}</Text>
          </Pressable>
        </View>

        {placeLabel ? (
          <View style={styles.pinned}>
            <Feather name="check-circle" size={15} color={colors.leaf} />
            <Text style={styles.pinnedText}>
              On the map at {placeLabel}. Tap either button again if that is not right.
            </Text>
          </View>
        ) : (
          <Text style={styles.hint}>
            Check-O sorts shops by how near they are, so it needs your shop on the map as well as in
            words. "Find my address" works the spot out from what you typed. "Use my location" reads
            your phone's position, which is only right if you are at the shop now.
          </Text>
        )}

        {locateNote ? (
          <Banner tone="warning" icon="map-pin">
            {locateNote}
          </Banner>
        ) : null}

        <View style={{ gap: 8 }}>
          <Text style={styles.label}>Do you deliver?</Text>
          <View style={styles.segment} accessibilityRole="radiogroup">
            {[
              { on: false, label: "They collect from me", icon: "shopping-bag" as const },
              { on: true, label: "I deliver", icon: "truck" as const },
            ].map((option) => {
              const selected = delivers === option.on;
              return (
                <Pressable
                  key={option.label}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                  onPress={() => setDelivers(option.on)}
                  style={[styles.segItem, selected && styles.segOn]}
                >
                  <Feather name={option.icon} size={17} color={selected ? colors.forest : colors.muted} />
                  <Text style={[styles.segText, selected && styles.segTextOn]}>{option.label}</Text>
                </Pressable>
              );
            })}
          </View>
          <Text style={styles.hint}>
            Check-O doesn't run riders. If you deliver, you arrange it yourself and keep the fee.
          </Text>
        </View>

        {delivers ? (
          <>
            <TextField
              label="What do you charge to deliver?"
              value={fee}
              onChangeText={(t) => setFee(t.replace(/[^0-9]/g, ""))}
              placeholder="500"
              keyboardType="number-pad"
            />
            <Text style={styles.hint}>
              One flat amount, added to the customer's total. Put 0 if you deliver free.
            </Text>
          </>
        ) : null}

        <TextField
          label="One line about your shop (optional)"
          value={tagline}
          onChangeText={setTagline}
          placeholder="Open 7am till 8pm, every day"
        />

        <Button
          title={editing ? "Save changes" : "Create my shop"}
          icon={editing ? "check" : "arrow-right"}
          loading={save.isPending}
          onPress={submit}
          style={{ marginTop: 6 }}
        />

        {!editing ? (
          <Text style={styles.hint}>
            Next you'll add your products. Once there's something on your shelf you can send your shop in
            to be checked.
          </Text>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  back: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.ink, letterSpacing: -0.6 },
  lead: { fontFamily: fonts.body, fontSize: 14.5, lineHeight: 21, color: colors.muted, marginTop: -8 },
  label: { fontFamily: fonts.bodySemibold, fontSize: 13.5, color: colors.ink },
  hint: { fontFamily: fonts.body, fontSize: 12.5, lineHeight: 18, color: colors.muted },

  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 999,
    borderWidth: 1.5,
    borderColor: colors.line,
    backgroundColor: colors.white,
  },
  chipOn: { borderColor: colors.leaf, backgroundColor: colors.mint },
  chipText: { fontFamily: fonts.bodyMedium, fontSize: 13, color: colors.muted },
  chipTextOn: { fontFamily: fonts.bodyBold, color: colors.leaf },

  locateRow: { flexDirection: "row", gap: 9 },
  locate: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    paddingHorizontal: 10,
    paddingVertical: 14,
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderStyle: "dashed",
    borderColor: colors.leaf,
    backgroundColor: colors.mint,
  },
  locateText: { fontFamily: fonts.bodySemibold, fontSize: 13, color: colors.leaf, textAlign: "center" },
  pinned: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    backgroundColor: colors.mint,
    borderRadius: radius.sm,
    padding: 11,
  },
  pinnedText: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 12.5, lineHeight: 18, color: colors.leaf },

  segment: { flexDirection: "row", gap: 8 },
  segItem: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    paddingVertical: 14,
    paddingHorizontal: 8,
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderColor: colors.line,
    backgroundColor: colors.white,
  },
  segOn: { borderColor: colors.leaf, backgroundColor: colors.mint },
  segText: { fontFamily: fonts.bodyMedium, fontSize: 13, color: colors.muted, textAlign: "center" },
  segTextOn: { fontFamily: fonts.bodyBold, color: colors.forest },
});
