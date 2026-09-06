import React from "react";
import { View, Text, StyleSheet, Platform } from "react-native";
import { Card, Divider, Button } from "react-native-paper";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { colors, gov } from "../constants/theme";
import type { Violation } from "../lib/types";

interface ViolationListProps {
  violations: Violation[];
  onViewEvidence?: (violation: Violation) => void;
}

type Kind = "high" | "medium" | "low" | "review";

const kindConfig: Record<Kind, { bg: string; fg: string; label: string; icon: any }> = {
  high: { bg: colors.dangerBg, fg: colors.danger, label: "HIGH", icon: "alert-octagon" },
  medium: { bg: colors.warningBg, fg: colors.warning, label: "MEDIUM", icon: "alert" },
  low: { bg: "#e2e8f0", fg: "#334155", label: "LOW", icon: "information" },
  review: { bg: "#dbeafe", fg: gov.navy, label: "NEEDS REVIEW", icon: "account-check" },
};

function kindOf(v: Violation): Kind {
  if (v.code?.endsWith("_REVIEW")) return "review";
  return (v.severity as Kind) || "low";
}

function splitMessage(msg: string): { text: string; ref?: string } {
  const i = msg.indexOf(" | Ref: ");
  if (i === -1) return { text: msg };
  return { text: msg.slice(0, i), ref: msg.slice(i + 8) };
}

export default function ViolationList({ violations, onViewEvidence }: ViolationListProps) {
  if (!violations || violations.length === 0) {
    return (
      <Card style={styles.emptyCard} mode="outlined">
        <Card.Content style={styles.emptyRow}>
          <MaterialCommunityIcons name="check-decagram" size={22} color={colors.success} />
          <Text style={styles.emptyText}>No non-compliances detected</Text>
        </Card.Content>
      </Card>
    );
  }

  const order: Kind[] = ["high", "medium", "low", "review"];
  const sorted = [...violations].sort((a, b) => order.indexOf(kindOf(a)) - order.indexOf(kindOf(b)));
  const violationCount = sorted.filter((v) => kindOf(v) !== "review").length;
  const reviewCount = sorted.length - violationCount;

  return (
    <Card style={styles.card} mode="outlined">
      <Card.Content>
        <View style={styles.titleRow}>
          <View style={styles.titleBar} />
          <Text style={styles.title}>Findings</Text>
        </View>
        <Text style={styles.summary}>
          {violationCount} violation{violationCount === 1 ? "" : "s"} · {reviewCount} item{reviewCount === 1 ? "" : "s"} for manual review
        </Text>

        {sorted.map((v, idx) => {
          const k = kindOf(v);
          const cfg = kindConfig[k];
          const { text, ref } = splitMessage(v.message || "");
          return (
            <View key={`${v.code}-${idx}`}>
              <View style={[styles.row, { borderLeftColor: cfg.fg }]}>
                <View style={styles.rowHeader}>
                  <View style={[styles.badge, { backgroundColor: cfg.bg }]}>
                    <MaterialCommunityIcons name={cfg.icon} size={13} color={cfg.fg} />
                    <Text style={[styles.badgeText, { color: cfg.fg }]}>{cfg.label}</Text>
                  </View>
                  <Text style={styles.code}>{v.code}</Text>
                </View>

                {v.field ? <Text style={styles.field}>{v.field.replace(/_/g, " ").toUpperCase()}</Text> : null}
                <Text style={styles.message}>{text}</Text>
                {ref ? (
                  <View style={styles.refRow}>
                    <MaterialCommunityIcons name="scale-balance" size={13} color={gov.navy} />
                    <Text style={styles.refText}>{ref}</Text>
                  </View>
                ) : null}
                <Text style={styles.meta}>Panel: {v.panelType || "—"}</Text>

                {onViewEvidence && v.imageId ? (
                  <Button mode="text" compact icon="image-search" onPress={() => onViewEvidence(v)} textColor={gov.navy} style={styles.evidenceBtn}>
                    View evidence
                  </Button>
                ) : null}
              </View>
              {idx < sorted.length - 1 && <Divider style={styles.divider} />}
            </View>
          );
        })}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: 16, backgroundColor: colors.surface, borderColor: colors.border },
  emptyCard: { marginBottom: 16, backgroundColor: colors.successBg, borderColor: "#86efac" },
  emptyRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  emptyText: { color: colors.success, fontWeight: "700", fontSize: 15 },
  titleRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 },
  titleBar: { width: 4, height: 18, backgroundColor: gov.saffron, borderRadius: 2 },
  title: { fontSize: 16, fontWeight: "800", color: gov.navy, textTransform: "uppercase", letterSpacing: 0.4 },
  summary: { fontSize: 12, color: colors.muted, marginBottom: 12 },
  row: { paddingVertical: 10, paddingLeft: 10, borderLeftWidth: 3 },
  rowHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" },
  badge: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  badgeText: { fontSize: 11, fontWeight: "800", letterSpacing: 0.3 },
  code: { fontSize: 11, color: colors.muted, fontFamily: Platform.OS === "ios" ? "Courier" : "monospace" },
  field: { fontSize: 11, fontWeight: "700", color: colors.muted, marginBottom: 2, letterSpacing: 0.4 },
  message: { fontSize: 14, color: colors.text, lineHeight: 20 },
  refRow: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: 4 },
  refText: { fontSize: 12, color: gov.navy, fontWeight: "600", fontStyle: "italic" },
  meta: { fontSize: 11, color: colors.muted, marginTop: 4 },
  evidenceBtn: { alignSelf: "flex-start", marginTop: 2, marginLeft: -8 },
  divider: { marginVertical: 4 },
});