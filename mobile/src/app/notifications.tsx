import { Feather } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button, EmptyState } from "../components/ui";
import { errorMessage } from "../config/api";
import { useStatusBar } from "../hooks/useStatusBar";
import {
  Notification,
  destinationOf,
  iconOf,
  notificationsService,
  whenOf,
} from "../services/notifications";
import { useAuth } from "../store/auth";
import { colors, fonts } from "../theme";

/**
 * Everything Check-O has ever tried to tell you.
 *
 * Shared by both sides of the app on purpose. A vendor is told when a shop is
 * approved and when stock runs low; a shopper is told when an order moves. They
 * are the same list of the same model, and splitting it in two would mean two
 * screens to keep in step for no gain.
 */
export default function Notifications() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const cache = useQueryClient();
  const selling = useAuth((s) => s.user?.role) === "vendor";

  /**
   * The inbox can be the first screen the app shows — reload Expo while it is
   * open and it comes back with nothing behind it. An unguarded `back()` then
   * throws "The action 'GO_BACK' was not handled by any navigator", which is
   * what the arrow did until 2026-10-10. Every other screen in Check-O already
   * checks; this one did not.
   */
  const leave = () =>
    router.canGoBack() ? router.back() : router.replace(selling ? "/(vendor)" : "/");

  const inbox = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationsService.list,
  });

  const refreshBadge = () => cache.invalidateQueries({ queryKey: ["notifications", "unread"] });

  const markRead = useMutation({
    mutationFn: notificationsService.markRead,
    // Show it read immediately — the tap is already taking her to another
    // screen, and waiting on the network to grey out a row she has left is
    // pointless. If the request fails the next refresh puts it back.
    onMutate: async (id: string) => {
      cache.setQueryData<Notification[]>(["notifications"], (rows) =>
        rows?.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
    },
    onSettled: refreshBadge,
  });

  const markAllRead = useMutation({
    mutationFn: notificationsService.markAllRead,
    onSuccess: () => {
      cache.setQueryData<Notification[]>(["notifications"], (rows) =>
        rows?.map((n) => ({ ...n, is_read: true })),
      );
      refreshBadge();
    },
  });

  const rows = inbox.data ?? [];
  const unread = rows.filter((n) => !n.is_read).length;

  function open(n: Notification) {
    if (!n.is_read) markRead.mutate(n.id);

    const to = destinationOf(n);
    if (!to) return;

    // A screen of its own goes on top, so Back returns here to the inbox.
    if (!to.inTabsBelow) {
      router.push(to.href as never);
      return;
    }

    // The destination is a tab sitting underneath the inbox. Pushing it only
    // switches the screen behind this one, so from the person's side nothing
    // happens at all. Closing the inbox and then navigating — the obvious
    // repair — is the one thing that cannot work: expo-router swallows a
    // navigate that follows a dismiss when the destination is in a group with
    // its own layout, which (vendor) and (tabs) both are (expo/expo#39517).
    // `replace` is a single call, so there is no second navigation to lose.
    router.replace(to.href as never);
  }

  if (inbox.isPending) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.sand }}
      data={rows}
      keyExtractor={(n) => n.id}
      contentContainerStyle={{
        paddingHorizontal: 20,
        paddingTop: insets.top + 14,
        paddingBottom: insets.bottom + 24,
        gap: 10,
      }}
      refreshControl={
        <RefreshControl
          refreshing={inbox.isRefetching}
          onRefresh={() => inbox.refetch()}
          tintColor={colors.leaf}
        />
      }
      ListHeaderComponent={
        <View style={{ gap: 12, marginBottom: 2 }}>
          <View style={styles.bar}>
            <Pressable
              onPress={leave}
              accessibilityRole="button"
              accessibilityLabel="Go back"
              hitSlop={10}
              style={styles.back}
            >
              <Feather name="arrow-left" size={22} color={colors.ink} />
            </Pressable>
            <Text style={styles.title}>Notifications</Text>
          </View>


          {rows.length > 0 ? (
            <Text style={styles.count}>
              {rows.length} {rows.length === 1 ? "message" : "messages"} ·{" "}
              {unread === 0 ? "all read" : `${unread} unread`}
            </Text>
          ) : null}

          {unread > 0 ? (
            <Pressable
              onPress={() => markAllRead.mutate()}
              disabled={markAllRead.isPending}
              accessibilityRole="button"
              style={styles.markAll}
            >
              <Feather name="check-circle" size={15} color={colors.leaf} />
              <Text style={styles.markAllText}>
                Mark {unread === 1 ? "it" : `all ${unread}`} as read
              </Text>
            </Pressable>
          ) : null}

          {inbox.isError ? (
            <>
              <Banner tone="danger" icon="wifi-off">
                {errorMessage(inbox.error)}
              </Banner>
              <Button title="Try again" variant="secondary" onPress={() => inbox.refetch()} />
            </>
          ) : null}
        </View>
      }
      ListEmptyComponent={
        inbox.isError ? null : (
          <EmptyState
            icon="bell"
            title="Nothing yet"
            body="When an order moves, a payment lands or Check-O has news about your shop, it shows up here."
          />
        )
      }
      renderItem={({ item }) => <Row n={item} onPress={() => open(item)} />}
    />
  );
}

function Row({ n, onPress }: { n: Notification; onPress: () => void }) {
  const goesSomewhere = destinationOf(n) !== null;
  const unread = !n.is_read;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole={goesSomewhere ? "link" : "button"}
      accessibilityLabel={`${n.title}. ${n.body}. ${unread ? "Unread" : "Read"}`}
      style={({ pressed }) => [
        styles.card,
        unread && styles.cardUnread,
        pressed && { opacity: 0.9 },
      ]}
    >
      <View style={[styles.icon, unread && { backgroundColor: colors.mint }]}>
        <Feather name={iconOf(n)} size={17} color={unread ? colors.leaf : colors.muted} />
      </View>

      <View style={{ flex: 1, gap: 3 }}>
        <View style={styles.head}>
          <Text style={[styles.rowTitle, unread && styles.rowTitleUnread]} numberOfLines={2}>
            {n.title}
          </Text>
          {unread ? <View style={styles.dot} /> : null}
        </View>

        {n.body ? (
          <Text style={styles.body} numberOfLines={3}>
            {n.body}
          </Text>
        ) : null}

        <View style={styles.foot}>
          <Text style={styles.when}>{whenOf(n.created_at)}</Text>
          {goesSomewhere ? (
            <Feather name="chevron-right" size={16} color={colors.muted} />
          ) : null}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
  bar: { flexDirection: "row", alignItems: "center", gap: 6 },
  back: { width: 34, height: 34, alignItems: "center", justifyContent: "center", marginLeft: -6 },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.ink, letterSpacing: -0.6 },
  count: { fontFamily: fonts.bodyMedium, fontSize: 13, color: colors.muted, marginTop: -6 },
  markAll: { flexDirection: "row", alignItems: "center", gap: 7, alignSelf: "flex-start" },
  markAllText: { fontFamily: fonts.bodySemibold, fontSize: 13.5, color: colors.leaf },
  card: {
    flexDirection: "row",
    gap: 12,
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
  },
  cardUnread: { borderColor: colors.leaf + "55", backgroundColor: colors.white },
  icon: {
    width: 36,
    height: 36,
    borderRadius: 999,
    backgroundColor: colors.sand,
    alignItems: "center",
    justifyContent: "center",
  },
  head: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  rowTitle: {
    flex: 1,
    fontFamily: fonts.bodySemibold,
    fontSize: 15,
    color: colors.ink,
    lineHeight: 20,
  },
  rowTitleUnread: { fontFamily: fonts.bodyBold },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 999,
    backgroundColor: colors.saffron,
    marginTop: 6,
  },
  body: { fontFamily: fonts.body, fontSize: 13.5, color: colors.muted, lineHeight: 19 },
  foot: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 2 },
  when: { fontFamily: fonts.bodyMedium, fontSize: 12, color: colors.muted },
});
