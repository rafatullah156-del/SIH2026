import { MD3LightTheme } from "react-native-paper";

export const gov = {
  navy: "#0b2a5b",
  navyDark: "#071c3d",
  saffron: "#ff9933",
  white: "#ffffff",
  green: "#138808",
  gold: "#d4a017",
  lightBg: "#f4f6fa",
};

export const colors = {
  primary: gov.navy,
  primaryDark: gov.navyDark,
  accent: gov.saffron,
  background: gov.lightBg,
  surface: "#ffffff",
  text: "#0f172a",
  muted: "#475569",
  border: "#d9dee7",
  success: "#15803d",
  successBg: "#dcfce7",
  warning: "#b45309",
  warningBg: "#fef3c7",
  danger: "#b91c1c",
  dangerBg: "#fee2e2",
};

export const paperTheme = {
  ...MD3LightTheme,
  roundness: 6,
  colors: {
    ...MD3LightTheme.colors,
    primary: colors.primary,
    onPrimary: "#ffffff",
    background: colors.background,
    surface: colors.surface,
    surfaceVariant: "#eef2f7",
    onSurface: colors.text,
    onSurfaceVariant: colors.muted,
    outline: colors.border,
    secondaryContainer: "#dbe4f3",
    onSecondaryContainer: colors.primaryDark,
    elevation: {
      ...MD3LightTheme.colors.elevation,
      level0: "transparent",
      level1: "#ffffff",
      level2: "#ffffff",
      level3: "#ffffff",
    },
  },
};