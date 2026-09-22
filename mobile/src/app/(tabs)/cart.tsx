import { router } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, EmptyState } from "../../components/ui";
import { useStatusBar } from "../../hooks/useStatusBar";
import { colors, fonts } from "../../theme";

// Stage 4 fills this with the real cart (grouped by shop) and checkout.
export default function Cart() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.page, { paddingTop: insets.top + 20 }]}>
      <Text style={styles.title}>Your cart</Text>
      <EmptyState
        icon="shopping-bag"
        title="Your cart is empty"
        body="Add items from any shop. You'll pay once, and each shop sends its own part."
        action={<Button title="Start shopping" onPress={() => router.navigate("/")} style={{ marginTop: 8, alignSelf: "stretch" }} />}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.sand, paddingHorizontal: 20 },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.ink, letterSpacing: -0.6 },
});
