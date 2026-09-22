import { Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { NearbyShop } from "../services/shops";
import { colors, fonts } from "../theme";
import { categoryStyle } from "./categories";

export function ShopCard({ shop }: { shop: NearbyShop }) {
  const look = categoryStyle(shop.category);
  const distance =
    shop.distance_km < 1 ? `${Math.round(shop.distance_km * 1000)} m` : `${shop.distance_km.toFixed(1)} km`;
  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`${shop.name}, ${shop.category_display}, ${distance} away`}
      onPress={() =>
        router.push({
          pathname: "/shop/[id]",
          params: { id: shop.business_id, name: shop.name, category: shop.category },
        })
      }
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.9 }]}
    >
        <View style={[styles.cover, { backgroundColor: look.tint }]}>
          <MaterialCommunityIcons name={look.icon} size={40} color={look.ink} />
        </View>
        <View style={styles.body}>
          <Text style={styles.name} numberOfLines={1}>
            {shop.name}
          </Text>
          <View style={styles.meta}>
            <Text style={styles.metaText} numberOfLines={1}>
              {shop.category_display} · {distance}
            </Text>
            {shop.avg_rating ? (
              <View style={styles.rating}>
                <Feather name="star" size={13} color={colors.saffron} />
                <Text style={styles.ratingText}>{shop.avg_rating.toFixed(1)}</Text>
              </View>
            ) : (
              <Text style={styles.newTag}>New</Text>
            )}
          </View>
        </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    width: 232,
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    overflow: "hidden",
  },
  cover: { height: 104, alignItems: "center", justifyContent: "center" },
  body: { paddingHorizontal: 14, paddingTop: 12, paddingBottom: 14, gap: 4 },
  name: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  meta: { flexDirection: "row", alignItems: "center", gap: 6 },
  metaText: { flex: 1, fontFamily: fonts.bodyMedium, fontSize: 13, color: colors.muted },
  rating: { flexDirection: "row", alignItems: "center", gap: 3 },
  ratingText: { fontFamily: fonts.bodyBold, fontSize: 13, color: colors.ink },
  newTag: { fontFamily: fonts.bodyBold, fontSize: 12, color: colors.leaf },
});
