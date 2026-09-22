import { Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { HOME_CATEGORIES } from "../../components/categories";
import { ShopCard } from "../../components/ShopCard";
import { Banner, Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { useUserLocation } from "../../hooks/useUserLocation";
import { shopsService } from "../../services/shops";
import { useAuth } from "../../store/auth";
import { colors, fonts } from "../../theme";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function Home() {
  useStatusBar("light");
  const insets = useSafeAreaInsets();
  const user = useAuth((s) => s.user);
  const location = useUserLocation();
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");

  const nearby = useQuery({
    queryKey: ["nearby", location.lat, location.lng, category],
    queryFn: () => shopsService.nearby({ lat: location.lat, lng: location.lng, category: category || undefined }),
    enabled: location.ready,
  });

  const submitSearch = () => {
    const q = query.trim();
    if (q) router.push({ pathname: "/search", params: { q } });
  };

  const activeCategory = HOME_CATEGORIES.find((c) => c.value === category);

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.sand }}
      contentContainerStyle={{ paddingBottom: 32 }}
      keyboardShouldPersistTaps="handled"
      refreshControl={
        <RefreshControl refreshing={nearby.isRefetching} onRefresh={() => nearby.refetch()} tintColor={colors.leaf} />
      }
    >
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 14 }]}>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.deliverTo}>{location.approximate ? "Showing shops around" : "Delivering to"}</Text>
            <View style={styles.locRow}>
              <Feather name="map-pin" size={17} color={colors.saffron} />
              <Text style={styles.locText} numberOfLines={1}>
                {location.ready ? location.label : "Finding you…"}
              </Text>
            </View>
          </View>
          <Pressable accessibilityRole="button" accessibilityLabel="Notifications" style={styles.bell}>
            <Feather name="bell" size={21} color={colors.white} />
          </Pressable>
        </View>
        <Text style={styles.hello}>
          {greeting()}
          {user?.first_name ? `, ${user.first_name}` : ""}
        </Text>
        <View style={styles.search}>
          <Feather name="search" size={20} color={colors.muted} />
          <TextInput
            accessibilityLabel="Search Check-O"
            placeholder="Search garri, chargers, paracetamol…"
            placeholderTextColor="#8A938E"
            value={query}
            onChangeText={setQuery}
            onSubmitEditing={submitSearch}
            returnKeyType="search"
            style={styles.searchInput}
          />
        </View>
      </View>

      <View style={styles.content}>
        {location.approximate && location.ready ? (
          <Banner tone="warning" icon="navigation">
            Turn on location to see shops nearest to you. Showing central Asaba for now.
          </Banner>
        ) : null}

        {/* Ask Check-O (AI assistant arrives in a later update) */}
        <View style={styles.ask} accessibilityLabel="Ask Check-O, coming soon">
          <View style={styles.askIcon}>
            <MaterialCommunityIcons name="star-four-points-outline" size={22} color={colors.ink} />
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={styles.askTitle}>Ask Check-O</Text>
            <Text style={styles.askBody}>"Where can I get a phone charger near DLA?"</Text>
          </View>
          <Text style={styles.soon}>Soon</Text>
        </View>

        {/* Categories */}
        <View style={styles.grid}>
          {HOME_CATEGORIES.map((c) => {
            const on = c.value === category && c.value !== "";
            return (
              <Pressable
                key={c.label}
                accessibilityRole="button"
                accessibilityState={{ selected: on }}
                accessibilityLabel={`${c.label} shops`}
                onPress={() => setCategory(c.value === category ? "" : c.value)}
                style={styles.cat}
              >
                <View style={[styles.catIcon, { backgroundColor: c.tint }, on && styles.catOn]}>
                  <MaterialCommunityIcons name={c.icon} size={28} color={c.ink} />
                </View>
                <Text style={[styles.catLabel, on && { color: colors.leaf, fontFamily: fonts.bodyBold }]}>{c.label}</Text>
              </Pressable>
            );
          })}
        </View>

        {/* Nearby shops */}
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>
            {activeCategory && activeCategory.value ? `${activeCategory.label} near you` : "Shops near you"}
          </Text>
          {category ? (
            <Pressable accessibilityRole="button" onPress={() => setCategory("")} hitSlop={10}>
              <Text style={styles.sectionLink}>Show all</Text>
            </Pressable>
          ) : null}
        </View>

        {!location.ready || nearby.isPending ? (
          <ActivityIndicator color={colors.leaf} style={{ marginVertical: 32 }} />
        ) : nearby.isError ? (
          <View style={{ gap: 12 }}>
            <Banner tone="danger" icon="wifi-off">{errorMessage(nearby.error)}</Banner>
            <Button title="Try again" variant="secondary" onPress={() => nearby.refetch()} />
          </View>
        ) : nearby.data.length === 0 ? (
          <EmptyState
            icon="map"
            title="No shops here yet"
            body={
              category
                ? "No shops in this category near you yet. Try another category."
                : "We're signing up shops across Asaba. Check back soon."
            }
          />
        ) : (
          <FlatList
            horizontal
            data={nearby.data}
            keyExtractor={(s) => s.business_id}
            renderItem={({ item }) => <ShopCard shop={item} />}
            ItemSeparatorComponent={() => <View style={{ width: 12 }} />}
            showsHorizontalScrollIndicator={false}
            style={{ marginHorizontal: -20 }}
            contentContainerStyle={{ paddingHorizontal: 20 }}
          />
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  header: {
    backgroundColor: colors.forest,
    paddingHorizontal: 20,
    paddingBottom: 22,
    gap: 16,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  headerRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  deliverTo: { fontFamily: fonts.bodyMedium, fontSize: 12, color: colors.leafSoft },
  locRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 2 },
  locText: { flexShrink: 1, fontFamily: fonts.bodyBold, fontSize: 16, color: colors.white },
  bell: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "rgba(255,255,255,0.16)",
    alignItems: "center",
    justifyContent: "center",
  },
  hello: { fontFamily: fonts.displayBold, fontSize: 28, color: colors.white, letterSpacing: -0.6 },
  search: {
    height: 52,
    borderRadius: 16,
    backgroundColor: colors.white,
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  searchInput: { flex: 1, fontFamily: fonts.body, fontSize: 15, color: colors.ink, paddingVertical: 0 },
  content: { paddingHorizontal: 20, paddingTop: 18, gap: 22 },
  ask: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    padding: 14,
    borderRadius: 18,
    backgroundColor: colors.saffronSoft,
    borderWidth: 1,
    borderColor: "#F1DCAE",
  },
  askIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: colors.saffron,
    alignItems: "center",
    justifyContent: "center",
  },
  askTitle: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  askBody: { fontFamily: fonts.body, fontSize: 13, color: colors.saffronInk },
  soon: {
    fontFamily: fonts.bodyBold,
    fontSize: 11,
    color: colors.saffronInk,
    backgroundColor: colors.white,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    overflow: "hidden",
  },
  grid: { flexDirection: "row", flexWrap: "wrap", rowGap: 16 },
  cat: { width: "25%", alignItems: "center", gap: 8 },
  catIcon: { width: 64, height: 64, borderRadius: 20, alignItems: "center", justifyContent: "center" },
  catOn: { borderWidth: 2, borderColor: colors.leaf },
  catLabel: { fontFamily: fonts.bodySemibold, fontSize: 12.5, color: colors.ink },
  sectionHead: { flexDirection: "row", alignItems: "baseline", justifyContent: "space-between" },
  sectionTitle: { fontFamily: fonts.displayBold, fontSize: 19, color: colors.ink, letterSpacing: -0.2 },
  sectionLink: { fontFamily: fonts.bodySemibold, fontSize: 14, color: colors.leaf },
});
