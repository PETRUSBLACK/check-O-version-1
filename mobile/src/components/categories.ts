import { MaterialCommunityIcons } from "@expo/vector-icons";

import { colors } from "../theme";

type IconName = keyof typeof MaterialCommunityIcons.glyphMap;

export interface CategoryLook {
  label: string;
  value: string; // backend BusinessCategory value ("" = all)
  icon: IconName;
  tint: string;
  ink: string;
}

// The Home screen category tiles, in display order.
export const HOME_CATEGORIES: CategoryLook[] = [
  { label: "Groceries", value: "supermarket", icon: "basket-outline", tint: "#F3E7CF", ink: "#7A5510" },
  { label: "Pharmacy", value: "pharmacy", icon: "pill", tint: "#DDEFE5", ink: colors.leaf },
  { label: "Kitchens", value: "restaurant", icon: "silverware-fork-knife", tint: "#F8E1D6", ink: "#8A3A16" },
  { label: "Phones", value: "electronics", icon: "cellphone", tint: "#E1E8F4", ink: colors.blue },
  { label: "Fashion", value: "fashion", icon: "hanger", tint: "#EDE3F3", ink: "#5B2F7A" },
  { label: "Beauty", value: "beauty", icon: "lipstick", tint: "#F6DDE5", ink: "#8A2448" },
  { label: "Health", value: "health", icon: "heart-pulse", tint: "#E4EBE8", ink: "#2E4A40" },
  { label: "All shops", value: "", icon: "dots-grid", tint: "#ECEAE3", ink: colors.ink },
];

const FALLBACK: CategoryLook = {
  label: "Shop",
  value: "",
  icon: "storefront-outline",
  tint: "#ECEAE3",
  ink: colors.ink,
};

export function categoryStyle(value: string): CategoryLook {
  return HOME_CATEGORIES.find((c) => c.value === value) ?? FALLBACK;
}
