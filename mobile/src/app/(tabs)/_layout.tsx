import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { Tabs } from "expo-router";
import { ColorValue } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { cartService, unitCount } from "../../services/cart";
import { colors, fonts } from "../../theme";

type IconName = keyof typeof Feather.glyphMap;

const tabIcon =
  (name: IconName) =>
  ({ color }: { color: ColorValue }) => <Feather name={name} size={24} color={color} />;

export default function TabsLayout() {
  const insets = useSafeAreaInsets();
  // Kept warm here so the badge is right the moment you leave a product page.
  const cart = useQuery({ queryKey: ["cart"], queryFn: cartService.get });
  const count = cart.data ? unitCount(cart.data) : 0;
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.leaf,
        tabBarInactiveTintColor: colors.muted,
        tabBarLabelStyle: { fontFamily: fonts.bodySemibold, fontSize: 12, lineHeight: 16 },
        tabBarStyle: {
          backgroundColor: colors.white,
          borderTopColor: colors.line,
          height: 64 + insets.bottom,
          paddingTop: 6,
          paddingBottom: Math.max(insets.bottom, 8),
        },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Home", tabBarIcon: tabIcon("home") }} />
      <Tabs.Screen name="orders" options={{ title: "Orders", tabBarIcon: tabIcon("file-text") }} />
      <Tabs.Screen
        name="cart"
        options={{
          title: "Cart",
          tabBarIcon: tabIcon("shopping-bag"),
          tabBarBadge: count > 0 ? count : undefined,
          tabBarBadgeStyle: { backgroundColor: colors.saffron, color: colors.ink, fontFamily: fonts.bodyBold },
        }}
      />
      <Tabs.Screen name="account" options={{ title: "Account", tabBarIcon: tabIcon("user") }} />
    </Tabs>
  );
}
