import { Feather } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
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

import { Banner, Button, TextField } from "../components/ui";
import { errorMessage } from "../config/api";
import { useStatusBar } from "../hooks/useStatusBar";
import { useAuth } from "../store/auth";
import { colors, fonts } from "../theme";

type Role = "customer" | "vendor";

export default function Register() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ role?: string }>();
  const register = useAuth((s) => s.register);

  const [role, setRole] = useState<Role>(params.role === "vendor" ? "vendor" : "customer");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!firstName.trim() || !lastName.trim() || !email.trim() || !password) {
      setError("Please fill in every field.");
      return;
    }
    if (password.length < 8) {
      setError("Your password needs at least 8 characters.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await register({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim().toLowerCase(),
        password,
        role,
      });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView
        contentContainerStyle={[styles.page, { paddingTop: insets.top + 12, paddingBottom: insets.bottom + 24 }]}
        keyboardShouldPersistTaps="handled"
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Back"
          onPress={() => (router.canGoBack() ? router.back() : router.replace("/sign-in"))}
          style={styles.back}
        >
          <Feather name="chevron-left" size={22} color={colors.ink} />
        </Pressable>

        <Text style={styles.title}>Create your account</Text>

        <View style={styles.segment} accessibilityRole="radiogroup">
          {(["customer", "vendor"] as Role[]).map((r) => {
            const on = role === r;
            return (
              <Pressable
                key={r}
                accessibilityRole="radio"
                accessibilityState={{ selected: on }}
                onPress={() => setRole(r)}
                style={[styles.segItem, on && styles.segOn]}
              >
                <Feather
                  name={r === "customer" ? "shopping-bag" : "home"}
                  size={18}
                  color={on ? colors.forest : colors.muted}
                />
                <Text style={[styles.segText, on && { color: colors.forest, fontFamily: fonts.bodyBold }]}>
                  {r === "customer" ? "I want to buy" : "I want to sell"}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {role === "vendor" ? (
          <Banner tone="info">
            After signing up you'll add your shop details. We review every shop before it goes live.
          </Banner>
        ) : null}
        {error ? <Banner tone="danger" icon="alert-circle">{error}</Banner> : null}

        <View style={{ flexDirection: "row", gap: 12 }}>
          <View style={{ flex: 1 }}>
            <TextField label="First name" value={firstName} onChangeText={setFirstName} autoComplete="given-name" />
          </View>
          <View style={{ flex: 1 }}>
            <TextField label="Last name" value={lastName} onChangeText={setLastName} autoComplete="family-name" />
          </View>
        </View>
        <TextField
          label="Email"
          value={email}
          onChangeText={setEmail}
          placeholder="you@example.com"
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
        />
        <TextField
          label="Password"
          value={password}
          onChangeText={setPassword}
          placeholder="At least 8 characters"
          secure
          autoComplete="new-password"
          onSubmitEditing={submit}
        />
        <Button title="Create account" onPress={submit} loading={loading} style={{ marginTop: 4 }} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: { paddingHorizontal: 24, gap: 16, backgroundColor: colors.sand, flexGrow: 1 },
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
  segment: { flexDirection: "row", gap: 8 },
  segItem: {
    flex: 1,
    height: 48,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.white,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  segOn: { borderWidth: 2, borderColor: colors.leaf, backgroundColor: colors.mint },
  segText: { fontFamily: fonts.bodySemibold, fontSize: 14, color: colors.ink },
});
