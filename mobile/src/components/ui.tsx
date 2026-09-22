import { Feather } from "@expo/vector-icons";
import { ReactNode, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
  ViewStyle,
} from "react-native";

import { colors, fonts, radius } from "../theme";

// ─── Logo ─────────────────────────────────────────────────────────────────────
export function Logo({ size = 28, onDark = false }: { size?: number; onDark?: boolean }) {
  const fg = onDark ? colors.white : colors.leaf;
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }} accessibilityRole="header">
      <View
        style={{
          width: size,
          height: size,
          borderRadius: size / 2,
          borderWidth: size / 7,
          borderColor: colors.saffron,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Feather name="check" size={size * 0.55} color={fg} />
      </View>
      <Text style={{ fontFamily: fonts.display, fontSize: size * 0.8, color: fg, letterSpacing: -0.4 }}>
        Check-O
      </Text>
    </View>
  );
}

// ─── Buttons ──────────────────────────────────────────────────────────────────
type ButtonProps = {
  title: string;
  onPress?: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger";
  icon?: keyof typeof Feather.glyphMap;
  style?: ViewStyle;
};

export function Button({ title, onPress, loading, disabled, variant = "primary", icon, style }: ButtonProps) {
  const isPrimary = variant === "primary";
  const bg = variant === "danger" ? colors.red : isPrimary ? colors.leaf : colors.white;
  const fg = isPrimary || variant === "danger" ? colors.white : colors.ink;
  const inactive = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inactive, busy: !!loading }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg, opacity: inactive ? 0.6 : pressed ? 0.88 : 1 },
        variant === "secondary" && { borderWidth: 1.5, borderColor: colors.line },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <>
          {icon ? <Feather name={icon} size={20} color={fg} /> : null}
          <Text style={[styles.buttonText, { color: fg }]}>{title}</Text>
        </>
      )}
    </Pressable>
  );
}

// ─── Text field ───────────────────────────────────────────────────────────────
type FieldProps = TextInputProps & { label: string; error?: string; secure?: boolean };

export function TextField({ label, error, secure, style, ...rest }: FieldProps) {
  const [hidden, setHidden] = useState(!!secure);
  const [focused, setFocused] = useState(false);
  return (
    <View style={{ gap: 6 }}>
      <Text style={styles.label}>{label}</Text>
      <View
        style={[
          styles.field,
          { borderColor: error ? colors.red : focused ? colors.leaf : colors.line },
        ]}
      >
        <TextInput
          accessibilityLabel={label}
          placeholderTextColor="#8A938E"
          secureTextEntry={hidden}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={[styles.input, style]}
          {...rest}
        />
        {secure ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={hidden ? "Show password" : "Hide password"}
            onPress={() => setHidden((h) => !h)}
            hitSlop={10}
            style={{ padding: 4 }}
          >
            <Feather name={hidden ? "eye" : "eye-off"} size={20} color={colors.muted} />
          </Pressable>
        ) : null}
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

// ─── Misc ─────────────────────────────────────────────────────────────────────
export function Banner({
  tone = "info",
  icon = "info",
  children,
}: {
  tone?: "info" | "warning" | "danger";
  icon?: keyof typeof Feather.glyphMap;
  children: ReactNode;
}) {
  const palette = {
    info: [colors.blueSoft, colors.blue],
    warning: [colors.saffronSoft, colors.saffronInk],
    danger: [colors.redSoft, colors.red],
  }[tone];
  return (
    <View style={[styles.banner, { backgroundColor: palette[0] }]} accessibilityRole="alert">
      <Feather name={icon} size={18} color={palette[1]} style={{ marginTop: 1 }} />
      <Text style={[styles.bannerText, { color: palette[1] }]}>{children}</Text>
    </View>
  );
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon: keyof typeof Feather.glyphMap;
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <View style={styles.empty}>
      <View style={styles.emptyIcon}>
        <Feather name={icon} size={30} color={colors.leaf} />
      </View>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyBody}>{body}</Text>
      {action}
    </View>
  );
}

const styles = StyleSheet.create({
  button: {
    height: 54,
    borderRadius: radius.md,
    paddingHorizontal: 20,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  buttonText: { fontFamily: fonts.bodyBold, fontSize: 16 },
  label: { fontFamily: fonts.bodySemibold, fontSize: 14, color: colors.ink },
  field: {
    height: 52,
    borderRadius: 14,
    borderWidth: 1.5,
    backgroundColor: colors.white,
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  input: { flex: 1, fontFamily: fonts.body, fontSize: 16, color: colors.ink, paddingVertical: 0 },
  error: { fontFamily: fonts.bodyMedium, fontSize: 13, color: colors.red },
  banner: {
    flexDirection: "row",
    gap: 10,
    alignItems: "flex-start",
    padding: 12,
    borderRadius: 14,
  },
  bannerText: { flex: 1, fontFamily: fonts.bodySemibold, fontSize: 13.5, lineHeight: 19 },
  empty: { alignItems: "center", paddingHorizontal: 32, paddingVertical: 48, gap: 10 },
  emptyIcon: {
    width: 72,
    height: 72,
    borderRadius: 24,
    backgroundColor: colors.mint,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 6,
  },
  emptyTitle: { fontFamily: fonts.displayBold, fontSize: 20, color: colors.ink, textAlign: "center" },
  emptyBody: {
    fontFamily: fonts.body,
    fontSize: 15,
    lineHeight: 22,
    color: colors.muted,
    textAlign: "center",
  },
});
