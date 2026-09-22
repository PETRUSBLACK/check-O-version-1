import { Feather } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Banner, Button, TextField } from "../components/ui";
import { errorMessage } from "../config/api";
import { useStatusBar } from "../hooks/useStatusBar";
import { authService } from "../services/auth";
import { colors, fonts } from "../theme";

export default function ForgotPassword() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!email.trim()) {
      setError("Enter the email you signed up with.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await authService.requestPasswordReset(email);
      setSent(true);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={[styles.page, { paddingTop: insets.top + 12 }]}>
      <Pressable accessibilityRole="button" accessibilityLabel="Back" onPress={() => router.back()} style={styles.back}>
        <Feather name="chevron-left" size={22} color={colors.ink} />
      </Pressable>
      <Text style={styles.title}>Reset your password</Text>
      <Text style={styles.body}>We'll email you a link to choose a new password.</Text>
      {sent ? (
        <Banner tone="info" icon="mail">
          If an account exists for {email.trim()}, a reset link is on its way. Check your inbox.
        </Banner>
      ) : null}
      {error ? <Banner tone="danger" icon="alert-circle">{error}</Banner> : null}
      <TextField
        label="Email"
        value={email}
        onChangeText={setEmail}
        placeholder="you@example.com"
        autoCapitalize="none"
        keyboardType="email-address"
        autoComplete="email"
        onSubmitEditing={submit}
      />
      <Button title={sent ? "Send again" : "Send reset link"} onPress={submit} loading={loading} />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, paddingHorizontal: 24, gap: 16, backgroundColor: colors.sand },
  back: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.ink, letterSpacing: -0.6 },
  body: { fontFamily: fonts.body, fontSize: 15, lineHeight: 22, color: colors.muted },
});
