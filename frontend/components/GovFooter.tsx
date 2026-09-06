import React from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { useBreakpoint } from "../lib/breakpoints";
import { gov } from "../constants/theme";

const LINKS = [
  { label: "About", path: "/settings" },
  { label: "Rules Reference", path: "/settings" },
  { label: "Help", path: "/settings" },
  { label: "Contact", path: "/settings" },
];

export default function GovFooter() {
  const router = useRouter();
  const { isDesktop } = useBreakpoint();

  return (
    <View style={styles.footer}>
      <View style={[styles.inner, isDesktop && styles.innerDesktop]}>
        <View style={styles.linksRow}>
          {LINKS.map((l, i) => (
            <React.Fragment key={l.label}>
              <Pressable onPress={() => router.push(l.path as any)}>
                <Text style={styles.link}>{l.label}</Text>
              </Pressable>
              {i < LINKS.length - 1 && <Text style={styles.sep}>|</Text>}
            </React.Fragment>
          ))}
        </View>

        <Text style={styles.disclaimerTitle}>Disclaimer</Text>
        <Text style={styles.disclaimer}>
          This is a prototype developed for Smart India Hackathon 2026 (Problem Statement SIH26034). Compliance results
          are generated automatically using OCR and rule-based checks and are advisory in nature. Final determination of
          non-compliance rests with the authorised Legal Metrology Officer as per the Legal Metrology Act, 2009 and the
          Legal Metrology (Packaged Commodities) Rules, 2011.
        </Text>

        <View style={styles.bottomRow}>
          <Text style={styles.meta}>© {new Date().getFullYear()} Legal Metrology Compliance Checker · Prototype v1.0</Text>
          <Text style={styles.meta}>Last updated: {new Date().toLocaleDateString("en-IN")}</Text>
        </View>
      </View>
      <View style={styles.tricolor}>
        <View style={[styles.stripe, { backgroundColor: gov.saffron }]} />
        <View style={[styles.stripe, { backgroundColor: gov.white }]} />
        <View style={[styles.stripe, { backgroundColor: gov.green }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  footer: { backgroundColor: gov.navyDark, marginTop: 24 },
  inner: { padding: 16 },
  innerDesktop: { maxWidth: 1100, width: "100%", alignSelf: "center" },
  linksRow: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: 8, marginBottom: 14 },
  link: { color: gov.white, fontSize: 13, fontWeight: "600" },
  sep: { color: "#64748b" },
  disclaimerTitle: { color: gov.saffron, fontSize: 12, fontWeight: "700", marginBottom: 4, textTransform: "uppercase" },
  disclaimer: { color: "#cbd5e1", fontSize: 12, lineHeight: 18 },
  bottomRow: { marginTop: 14, borderTopWidth: 1, borderTopColor: "#1e3a5f", paddingTop: 10, gap: 4 },
  meta: { color: "#94a3b8", fontSize: 11 },
  tricolor: { flexDirection: "row", height: 4 },
  stripe: { flex: 1 },
});