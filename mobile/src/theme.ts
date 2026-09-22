// Check-O design tokens — match the style guide in the app design.

export const colors = {
  forest: "#0B3D2E", // headers, vendor app
  leaf: "#13614A", // buttons, links, active
  leafSoft: "#D5E8DE", // text on forest
  mint: "#EAF3EE", // selected / soft fills
  saffron: "#F4B23E", // highlights, badges
  saffronSoft: "#FDF3DF",
  saffronInk: "#6B4A06",
  sand: "#F6F4EE", // app background
  white: "#FFFFFF",
  ink: "#16201C", // text
  muted: "#5A6660", // secondary text
  line: "#E4E1D8", // borders
  red: "#B42318",
  redSoft: "#FDECEA",
  blue: "#1D4E89",
  blueSoft: "#E6EEF7",
} as const;

export const fonts = {
  display: "BricolageGrotesque_800ExtraBold",
  displayBold: "BricolageGrotesque_700Bold",
  body: "Figtree_400Regular",
  bodyMedium: "Figtree_500Medium",
  bodySemibold: "Figtree_600SemiBold",
  bodyBold: "Figtree_700Bold",
} as const;

export const radius = { sm: 12, md: 16, lg: 18, xl: 28 } as const;

export const naira = (value: string | number) =>
  "₦" + Number(value).toLocaleString("en-NG", { maximumFractionDigits: 0 });
