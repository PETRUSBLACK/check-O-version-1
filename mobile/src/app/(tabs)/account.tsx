import { Feather } from "@expo/vector-icons";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button } from "../../components/ui";
import { API_BASE_URL } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { useAuth } from "../../store/auth";
import { colors, fonts } from "../../theme";

export default function Account() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const user = useAuth((s) => s.user);
  const signOut = useAuth((s) => s.signOut);
  const [busy, setBusy] = useState(false);

  const initials = `${user?.first_name?.[0] ?? ""}${user?.last_name?.[0] ?? ""}`.toUpperCase() || "?";

  return (
    <View style={[styles.page, { paddingTop: insets.top + 20 }]}>
      <Text style={styles.title}>Account</Text>

      <View style={styles.card}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={styles.name}>
            {user?.first_name} {user?.last_name}
          </Text>
          <Text style={styles.email}>{user?.email}</Text>
        </View>
        <View style={styles.role}>
          <Feather name={user?.role === "vendor" ? "home" : "user"} size={13} color={colors.leaf} />
          <Text style={styles.roleText}>{user?.role === "vendor" ? "Seller" : "Customer"}</Text>
        </View>
      </View>

      {user?.role === "vendor" ? (
        <Banner tone="info">Your seller tools (orders, stock and the Check-O basket) are coming in the next update.</Banner>
      ) : null}

      <View style={{ flex: 1 }} />

      <Button
        title="Sign out"
        variant="secondary"
        icon="log-out"
        loading={busy}
        onPress={async () => {
          setBusy(true);
          await signOut();
        }}
      />
      {__DEV__ ? <Text style={styles.dev}>Server: {API_BASE_URL}</Text> : null}
      <View style={{ height: 16 }} />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.sand, paddingHorizontal: 20, gap: 16 },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.ink, letterSpacing: -0.6 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    padding: 16,
    borderRadius: 18,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.line,
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.forest,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { fontFamily: fonts.displayBold, fontSize: 18, color: colors.white },
  name: { fontFamily: fonts.bodyBold, fontSize: 16, color: colors.ink },
  email: { fontFamily: fonts.body, fontSize: 14, color: colors.muted },
  role: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: colors.mint,
  },
  roleText: { fontFamily: fonts.bodySemibold, fontSize: 12, color: colors.leaf },
  dev: { fontFamily: fonts.body, fontSize: 12, color: colors.muted, textAlign: "center" },
});
