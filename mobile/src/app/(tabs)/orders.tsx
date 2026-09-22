import { router } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, EmptyState } from "../../components/ui";
import { useStatusBar } from "../../hooks/useStatusBar";
import { colors, fonts } from "../../theme";

// Stage 5 fills this with real orders from /api/orders/.
export default function Orders() {
  useStatusBar("dark");
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.page, { paddingTop: insets.top + 20 }]}>
      <Text style={styles.title}>My orders</Text>
      <EmptyState
        icon="file-text"
        title="No orders yet"
        body="When you buy from a shop, you'll track it here — including your pickup code."
        action={<Button title="Find shops near you" onPress={() => router.navigate("/")} style={{ marginTop: 8, alignSelf: "stretch" }} />}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.sand, paddingHorizontal: 20 },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.ink, letterSpacing: -0.6 },
});
