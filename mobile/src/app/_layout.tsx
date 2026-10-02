import {
  BricolageGrotesque_700Bold,
  BricolageGrotesque_800ExtraBold,
} from "@expo-google-fonts/bricolage-grotesque";
import {
  Figtree_400Regular,
  Figtree_500Medium,
  Figtree_600SemiBold,
  Figtree_700Bold,
} from "@expo-google-fonts/figtree";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { useAuth } from "../store/auth";
import { colors } from "../theme";

SplashScreen.preventAutoHideAsync().catch(() => {});

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 60_000 } },
});

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    BricolageGrotesque_700Bold,
    BricolageGrotesque_800ExtraBold,
    Figtree_400Regular,
    Figtree_500Medium,
    Figtree_600SemiBold,
    Figtree_700Bold,
  });
  const status = useAuth((s) => s.status);
  const user = useAuth((s) => s.user);
  const bootstrap = useAuth((s) => s.bootstrap);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const ready = fontsLoaded && status !== "loading";

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  if (!ready) return null;

  const signedIn = status === "signedIn";
  // One app, two sides. A seller lands on their orders, not on shopping.
  const selling = signedIn && user?.role === "vendor";

  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.sand } }}>
          <Stack.Protected guard={!signedIn}>
            <Stack.Screen name="sign-in" />
            <Stack.Screen name="register" />
            <Stack.Screen name="forgot-password" />
          </Stack.Protected>
          <Stack.Protected guard={selling}>
            <Stack.Screen name="(vendor)" />
            <Stack.Screen name="vendor-order/[id]" />
            <Stack.Screen name="vendor-product/[id]" />
            <Stack.Screen name="vendor-product/new" />
            <Stack.Screen name="shop-setup" />
          </Stack.Protected>
          <Stack.Protected guard={signedIn && !selling}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="shop/[id]" />
            <Stack.Screen name="product/[id]" />
            <Stack.Screen name="order/[id]" />
            <Stack.Screen name="checkout" />
            <Stack.Screen name="order-placed" />
            <Stack.Screen name="pay" />
            <Stack.Screen name="search" />
          </Stack.Protected>
        </Stack>
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
