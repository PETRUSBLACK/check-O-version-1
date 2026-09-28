import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { Tabs } from "expo-router";
import { ColorValue } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ordersService } from "../../services/orders";
import { needsAction } from "../../services/vendor";
import { colors, fonts } from "../../theme";

type IconName = keyof typeof Feather.glyphMap;

const tabIcon =
  (name: IconName) =>
  ({ color }: { color: ColorValue }) => <Feather name={name} size={24} color={color} />;

export default function VendorTabsLayout() {
  const insets = useSafeAreaInsets();

  // The badge is the whole point of the seller app: a shop must know, without
  // looking, that something is waiting for them.
  const orders = useQuery({ queryKey: ["vendor-orders"], queryFn: ordersService.list });
  const waiting = (orders.data ?? []).filter(needsAction).length;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.saffron,
        tabBarInactiveTintColor: "rgba(255,255,255,0.65)",
        tabBarLabelStyle: { fontFamily: fonts.bodySemibold, fontSize: 12, lineHeight: 16 },
        tabBarStyle: {
          // The seller app wears the dark green, so a shop owner can tell at a
          // glance which side of Check-O they're looking at.
          backgroundColor: colors.forest,
          borderTopColor: "rgba(255,255,255,0.12)",
          height: 64 + insets.bottom,
          paddingTop: 6,
          paddingBottom: Math.max(insets.bottom, 8),
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Orders",
          tabBarIcon: tabIcon("inbox"),
          tabBarBadge: waiting > 0 ? waiting : undefined,
          tabBarBadgeStyle: {
            backgroundColor: colors.saffron,
            color: colors.ink,
            fontFamily: fonts.bodyBold,
          },
        }}
      />
      <Tabs.Screen name="products" options={{ title: "Products", tabBarIcon: tabIcon("package") }} />
      <Tabs.Screen name="shop" options={{ title: "My shop", tabBarIcon: tabIcon("home") }} />
      <Tabs.Screen name="account" options={{ title: "Account", tabBarIcon: tabIcon("user") }} />
    </Tabs>
  );
}
