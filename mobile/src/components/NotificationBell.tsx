import { Feather } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { notificationsService } from "../services/notifications";
import { colors, fonts } from "../theme";

/**
 * The bell, with the count of unread messages on it.
 *
 * Deliberately a header button and not a fifth tab: the shopper's tabs are the
 * four things she does (look, order, pay, account) and notifications are not a
 * place she goes, they are a thing that arrives.
 *
 * The count is its own query, kept out of the inbox's query so this can sit on
 * any screen without dragging the whole list over the network with it.
 */
export function NotificationBell({ onDark = false }: { onDark?: boolean }) {
  const unread = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: notificationsService.unreadCount,
    // Cheap, and it should be close to right when she comes back to a screen.
    staleTime: 30_000,
    refetchOnMount: true,
    // A failure here must never be visible: a bell with no number is fine, an
    // error banner over the Home screen because a count did not load is not.
    retry: false,
  });

  const count = unread.data ?? 0;
  const tint = onDark ? colors.leafSoft : colors.ink;

  return (
    <Pressable
      onPress={() => router.push("/notifications")}
      accessibilityRole="button"
      accessibilityLabel={
        count > 0
          ? `Notifications, ${count} unread`
          : "Notifications"
      }
      hitSlop={10}
      style={({ pressed }) => [styles.button, pressed && { opacity: 0.6 }]}
    >
      <Feather name="bell" size={22} color={tint} />
      {count > 0 ? (
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{count > 9 ? "9+" : count}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: { width: 36, height: 36, alignItems: "center", justifyContent: "center" },
  badge: {
    position: "absolute",
    top: 2,
    right: 1,
    minWidth: 17,
    height: 17,
    borderRadius: 999,
    paddingHorizontal: 4,
    backgroundColor: colors.saffron,
    alignItems: "center",
    justifyContent: "center",
  },
  badgeText: { fontFamily: fonts.bodyBold, fontSize: 10.5, color: colors.ink },
});
