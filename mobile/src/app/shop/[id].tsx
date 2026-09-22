import { Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { categoryStyle } from "../../components/categories";
import { EmptyState } from "../../components/ui";
import { useStatusBar } from "../../hooks/useStatusBar";
import { colors, fonts } from "../../theme";

// Stage 3 adds the shop's products, hours and ratings here.
export default function ShopScreen() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const { name, category } = useLocalSearchParams<{ id: string; name?: string; category?: string }>();
  const look = categoryStyle(category ?? "");

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.sand }}>
      <View style={[styles.cover, { backgroundColor: look.tint, paddingTop: insets.top }]}>
        <MaterialCommunityIcons name={look.icon} size={64} color={look.ink} />
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
        <Text style={styles.name}>{name ?? "Shop"}</Text>
        <EmptyState
          icon="package"
          title="Products are on the way"
          body="This shop's products, opening hours and reviews will show here in the next update."
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  cover: { height: 220, alignItems: "center", justifyContent: "center" },
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
  },
  name: { fontFamily: fonts.display, fontSize: 26, color: colors.ink, letterSpacing: -0.5 },
});
