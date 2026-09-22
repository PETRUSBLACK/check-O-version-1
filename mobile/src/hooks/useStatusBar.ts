import { useFocusEffect } from "expo-router";
import { setStatusBarStyle, StatusBarStyle } from "expo-status-bar";
import { useCallback } from "react";

/** Sets the status-bar icon colour while this screen is focused. */
export function useStatusBar(style: StatusBarStyle) {
  useFocusEffect(
    useCallback(() => {
      setStatusBarStyle(style);
    }, [style]),
  );
}
