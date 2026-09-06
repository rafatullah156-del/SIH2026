import React from "react";
import { View, Text, StyleSheet, Pressable, Platform } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter, usePathname } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useBreakpoint } from "../lib/breakpoints";
import { gov } from "../constants/theme";

// To use a real emblem later:
//   import { Image } from "react-native";
//   <Image source={require("../assets/images/emblem.png")} style={styles.emblemImg} />
// and replace <MaterialCommunityIcons name="shield-star" .../> below.

const NAV_LINKS = [
  { label: "Home", path: "/" },
  { label: "History", path: "/history" },
  { label: "Settings", path: "/settings" },
];

export default function GovHeader() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const pathname = usePathname();
  const { isDesktop, isPhone } = useBreakpoint();

  return (
    <View style={{ paddingTop: insets.top, backgroundColor: gov.white }}>
      {/* Tricolor strip */}
      <View style={styles.tricolor}>
        <View style={[styles.stripe, { backgroundColor: gov.saffron }]} />
        <View style={[styles.stripe, { backgroundColor: gov.white }]} />
        <View style={[styles.stripe, { backgroundColor: gov.green }]} />
      </View>

      {/* Ministry row */}
      <View style={[styles.ministryRow, isDesktop && styles.rowDesktop]}>
        <View style={styles.ministryLeft}>
          <View style={styles.emblemBox}>
            <MaterialCommunityIcons name="shield-star" size={isPhone ? 34 : 44} color={gov.navy} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.govLine}>भारत सरकार | Government of India</Text>
            <Text style={styles.ministryLine} numberOfLines={2}>
              Ministry of Consumer Affairs, Food & Public Distribution
            </Text>
            <Text style={styles.deptLine}>Department of Consumer Affairs · Legal Metrology Division</Text>
          </View>
        </View>

        {isDesktop && (
          <View style={styles.navRow}>
            {NAV_LINKS.map((l) => {
              const active = pathname === l.path;
              return (
                <Pressable key={l.path} onPress={() => router.push(l.path as any)} style={styles.navBtn}>
                  <Text style={[styles.navText, active && styles.navTextActive]}>{l.label}</Text>
                </Pressable>
              );
            })}
          </View>
        )}
      </View>

      {/* Title band */}
      <View style={styles.titleBand}>
        <View style={[styles.titleInner, isDesktop && styles.rowDesktop]}>
          <View style={{ flex: 1 }}>
            <Text style={styles.titleEn}>Legal Metrology Compliance Checker</Text>
            <Text style={styles.titleHi}>विधिक माप विज्ञान अनुपालन जाँच प्रणाली</Text>
          </View>
          <View style={styles.rulePill}>
            <MaterialCommunityIcons name="scale-balance" size={14} color={gov.navy} />
            <Text style={styles.rulePillText}>Packaged Commodities Rules, 2011</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  tricolor: { flexDirection: "row", height: 5 },
  stripe: { flex: 1 },
  ministryRow: { paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: "#e2e8f0" },
  rowDesktop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", maxWidth: 1100, width: "100%", alignSelf: "center" },
  ministryLeft: { flexDirection: "row", alignItems: "center", gap: 12, flex: 1 },
  emblemBox: { width: 52, height: 52, borderRadius: 26, backgroundColor: "#eef2f7", alignItems: "center", justifyContent: "center" },
  emblemImg: { width: 48, height: 48, resizeMode: "contain" },
  govLine: { fontSize: 11, color: "#475569", fontWeight: "600", letterSpacing: 0.3 },
  ministryLine: { fontSize: 14, fontWeight: "700", color: gov.navy, marginTop: 1 },
  deptLine: { fontSize: 11, color: "#475569", marginTop: 1 },
  navRow: { flexDirection: "row", gap: 4 },
  navBtn: { paddingHorizontal: 12, paddingVertical: 6 },
  navText: { fontSize: 14, fontWeight: "600", color: "#334155" },
  navTextActive: { color: gov.navy, textDecorationLine: "underline" },
  titleBand: { backgroundColor: gov.navy, borderBottomWidth: 3, borderBottomColor: gov.saffron },
  titleInner: { paddingHorizontal: 16, paddingVertical: 12, gap: 8 },
  titleEn: { color: gov.white, fontSize: 18, fontWeight: "800", letterSpacing: 0.2 },
  titleHi: { color: "#cbd5e1", fontSize: 13, marginTop: 2 },
  rulePill: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: gov.white, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 4, alignSelf: "flex-start" },
  rulePillText: { fontSize: 12, fontWeight: "700", color: gov.navy },
});