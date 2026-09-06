import { useWindowDimensions } from "react-native";

export const BREAKPOINTS = {
  phone: 600,
  tablet: 1024,
};

export type DeviceType = "phone" | "tablet" | "desktop";

export function useDeviceType(): DeviceType {
  const { width } = useWindowDimensions();
  if (width < BREAKPOINTS.phone) return "phone";
  if (width < BREAKPOINTS.tablet) return "tablet";
  return "desktop";
}

export function useBreakpoint() {
  const { width, height } = useWindowDimensions();
  const deviceType = useDeviceType();
  return {
    width,
    height,
    deviceType,
    isPhone: deviceType === "phone",
    isTablet: deviceType === "tablet",
    isDesktop: deviceType === "desktop",
  };
}