import { Feather } from "@expo/vector-icons";
import { Link } from "expo-router";
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button, Logo, TextField } from "../components/ui";
import { errorMessage } from "../config/api";
import { useStatusBar } from "../hooks/useStatusBar";
import { useAuth } from "../store/auth";
import { colors, fonts } from "../theme";

// Sign in — the first screen for signed-out users.
export default function SignIn() {
  useStatusBar("light");
  const insets = useSafeAreaInsets();
  const signIn = useAuth((s) => s.signIn);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await signIn(email, password);
    } catch (e) {
      setError(
        (e as any)?.response?.status === 401
          ? "That email and password don't match. Try again."
          : errorMessage(e),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.forest }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={{ flexGrow: 1 }} keyboardShouldPersistTaps="handled">
        <View style={[styles.hero, { paddingTop: insets.top + 32 }]}>
          <View style={styles.ring} />
          <View style={styles.dot} />
          <Logo size={34} onDark />
          <Text style={styles.headline}>Everything in Asaba, near you.</Text>
          <Text style={styles.sub}>Order from shops, markets and pharmacies. Delivered, or ready for pickup.</Text>
        </View>

        <View style={[styles.sheet, { paddingBottom: insets.bottom + 24 }]}>
          <Text style={styles.title}>Sign in</Text>
          {error ? <Banner tone="danger" icon="alert-circle">{error}</Banner> : null}
          <TextField
            label="Email"
            value={email}
            onChangeText={setEmail}
            placeholder="you@example.com"
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            textContentType="emailAddress"
            returnKeyType="next"
          />
          <TextField
            label="Password"
            value={password}
            onChangeText={setPassword}
            placeholder="Your password"
            secure
            autoComplete="current-password"
            textContentType="password"
            returnKeyType="go"
            onSubmitEditing={submit}
          />
          <Link href="/forgot-password" asChild>
            <Pressable accessibilityRole="link" style={{ alignSelf: "flex-end" }} hitSlop={8}>
              <Text style={styles.link}>Forgot password?</Text>
            </Pressable>
          </Link>
          <Button title="Sign in" onPress={submit} loading={loading} />
          <View style={styles.row}>
            <Text style={styles.muted}>New to Check-O? </Text>
            <Link href="/register" asChild>
              <Pressable accessibilityRole="link" hitSlop={8}>
                <Text style={styles.linkBold}>Create an account</Text>
              </Pressable>
            </Link>
          </View>
          <Link href={{ pathname: "/register", params: { role: "vendor" } }} asChild>
            <Pressable accessibilityRole="link" style={styles.sell} hitSlop={8}>
              <Feather name="shopping-bag" size={18} color={colors.leaf} />
              <Text style={styles.sellText}>Sell on Check-O — open your shop</Text>
            </Pressable>
          </Link>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  hero: { paddingHorizontal: 28, paddingBottom: 56, gap: 18, overflow: "hidden" },
  ring: {
    position: "absolute",
    width: 320,
    height: 320,
    borderRadius: 160,
    borderWidth: 44,
    borderColor: colors.leaf,
    right: -120,
    top: -90,
  },
  dot: {
    position: "absolute",
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: colors.saffron,
    right: 36,
    bottom: -84,
  },
  headline: {
    fontFamily: fonts.display,
    fontSize: 36,
    lineHeight: 38,
    letterSpacing: -1,
    color: colors.white,
    maxWidth: 320,
  },
  sub: { fontFamily: fonts.body, fontSize: 16, lineHeight: 24, color: colors.leafSoft, maxWidth: 300 },
  sheet: {
    flexGrow: 1,
    backgroundColor: colors.sand,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    marginTop: -28,
    paddingHorizontal: 24,
    paddingTop: 26,
    gap: 16,
  },
  title: { fontFamily: fonts.display, fontSize: 24, color: colors.ink, letterSpacing: -0.4 },
  link: { fontFamily: fonts.bodySemibold, fontSize: 14, color: colors.leaf },
  linkBold: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.leaf },
  row: { flexDirection: "row", justifyContent: "center", alignItems: "center" },
  muted: { fontFamily: fonts.body, fontSize: 14, color: colors.muted },
  sell: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, marginTop: 8, minHeight: 44 },
  sellText: { fontFamily: fonts.bodySemibold, fontSize: 14, color: colors.ink },
});
