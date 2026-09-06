import React from "react";
import { View, Text, StyleSheet, ScrollView, RefreshControl, Pressable } from "react-native";
import { Button, ActivityIndicator } from "react-native-paper";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useBreakpoint } from "../../lib/breakpoints";
import GovFooter from "../../components/GovFooter";
import { colors, gov } from "../../constants/theme";
import type { ScanListItem } from "../../lib/types";

const DECLARATIONS = [
  { icon: "currency-inr", label: "MRP (₹)" },
  { icon: "weight-gram", label: "Net Quantity" },
  { icon: "calendar-month", label: "MFD / PKD / IMP Date" },
  { icon: "factory", label: "Manufacturer / Packer / Importer" },
  { icon: "phone", label: "Consumer Care Details" },
];

const NOTICES = [
  "Capture label images in good lighting; avoid glare and shadows.",
  "Include a calibration image (credit card or printed marker) to enable font-size verification.",
  "Use the Phone Camera (QR) option on laptops for higher-quality captures.",
];

const statusStyle: Record<string, { bg: string; fg: string; label: string }> = {
  created: { bg: "#e2e8f0", fg: "#334155", label: "Created" },
  uploading: { bg: "#dbeafe", fg: "#1e40af", label: "Uploading" },
  queued: { bg: "#fef3c7", fg: "#92400e", label: "Queued" },
  processing: { bg: "#fef3c7", fg: "#92400e", label: "Processing" },
  done: { bg: colors.successBg, fg: colors.success, label: "Completed" },
  failed: { bg: colors.dangerBg, fg: colors.danger, label: "Failed" },
};

function StatCard({ icon, label, value, tint }: { icon: any; label: string; value: string; tint: string }) {
  return (
    <View style={[styles.statCard, { borderTopColor: tint }]}>
      <MaterialCommunityIcons name={icon} size={22} color={tint} />
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function SectionTitle({ children }: { children: string }) {
  return (
    <View style={styles.sectionTitleRow}>
      <View style={styles.sectionBar} />
      <Text style={styles.sectionTitle}>{children}</Text>
    </View>
  );
}

export default function HomeScreen() {
  const router = useRouter();
  const { isDesktop, isTablet } = useBreakpoint();
  const wide = isDesktop || isTablet;

  const scansQ = useQuery({
    queryKey: ["scans", "recent"],
    queryFn: () => api.listScans({ page: 1, pageSize: 6 }),
  });

  const summaryQ = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => api.getDashboardSummary(),
    retry: false,
  });

  const scans = scansQ.data || [];
  const s = summaryQ.data;

  const doneScans = scans.filter((x) => x.status === "done" && typeof x.score === "number");
  const localAvg = doneScans.length
    ? Math.round(doneScans.reduce((a, x) => a + (x.score || 0), 0) / doneScans.length)
    : null;
  const pending = scans.filter((x) => !["done", "failed"].includes(x.status)).length;

  const totalScans = s?.totalScans ?? scans.length;
  const totalViolations = s?.totalViolations;
  const avgScore = s?.averageScore ?? localAvg;

  const refresh = () => {
    scansQ.refetch();
    summaryQ.refetch();
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={scansQ.isRefetching} onRefresh={refresh} />}
    >
      <View style={[styles.inner, isDesktop && styles.innerDesktop]}>
        {/* Primary actions */}
        <View style={styles.heroCard}>
          <View style={{ flex: 1 }}>
            <Text style={styles.heroTitle}>Verify Packaged Commodity Labels</Text>
            <Text style={styles.heroSub}>
              Automated detection of mandatory declarations and non-compliances with evidence-backed digital reports.
            </Text>
          </View>
          <View style={[styles.heroActions, wide && styles.heroActionsWide]}>
            <Button mode="contained" icon="camera-plus" onPress={() => router.push("/scan/new")} contentStyle={styles.bigBtn} style={styles.actionBtn}>
              New Scan
            </Button>
            <Button
              mode="outlined"
              icon="qrcode-scan"
              onPress={() => router.push({ pathname: "/scan/new", params: { qr: "1" } })}
              contentStyle={styles.bigBtn}
              style={styles.actionBtn}
              textColor={gov.navy}
            >
              Use Phone Camera (QR)
            </Button>
          </View>
        </View>

        {/* Stats */}
        <SectionTitle>Overview</SectionTitle>
        <View style={styles.statsRow}>
          <StatCard icon="file-document-multiple" label="Total Scans" value={String(totalScans)} tint={gov.navy} />
          <StatCard icon="alert-circle" label="Violations Found" value={totalViolations != null ? String(totalViolations) : "—"} tint={colors.danger} />
          <StatCard icon="chart-donut" label="Avg. Compliance" value={avgScore != null ? `${avgScore}%` : "—"} tint={colors.success} />
          <StatCard icon="progress-clock" label="In Progress" value={String(pending)} tint={colors.warning} />
        </View>

        <View style={[wide && styles.twoCol]}>
          {/* Left column */}
          <View style={[wide && styles.col]}>
            <SectionTitle>Mandatory Declarations Verified</SectionTitle>
            <View style={styles.panel}>
              {DECLARATIONS.map((d) => (
                <View key={d.label} style={styles.declRow}>
                  <MaterialCommunityIcons name={d.icon as any} size={18} color={gov.navy} />
                  <Text style={styles.declText}>{d.label}</Text>
                  <MaterialCommunityIcons name="check-circle" size={16} color={colors.success} />
                </View>
              ))}
              <Text style={styles.declFoot}>As per Rule 6, Legal Metrology (Packaged Commodities) Rules, 2011</Text>
            </View>

            <SectionTitle>Important Notices</SectionTitle>
            <View style={[styles.panel, styles.noticePanel]}>
              {NOTICES.map((n, i) => (
                <View key={i} style={styles.noticeRow}>
                  <Text style={styles.noticeBullet}>▸</Text>
                  <Text style={styles.noticeText}>{n}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* Right column */}
          <View style={[wide && styles.col]}>
            <View style={styles.recentHeader}>
              <SectionTitle>Recent Scans</SectionTitle>
              <Pressable onPress={() => router.push("/history")}>
                <Text style={styles.viewAll}>View all →</Text>
              </Pressable>
            </View>

            <View style={styles.panel}>
              {scansQ.isLoading ? (
                <ActivityIndicator style={{ marginVertical: 20 }} />
              ) : scansQ.isError ? (
                <Text style={styles.errorText}>Unable to reach the server. Pull to refresh.</Text>
              ) : scans.length === 0 ? (
                <Text style={styles.emptyText}>No scans recorded yet. Start with "New Scan".</Text>
              ) : (
                scans.map((scan: ScanListItem, idx) => {
                  const st = statusStyle[scan.status] || statusStyle.created;
                  return (
                    <Pressable
                      key={scan.scanId}
                      onPress={() => router.push(`/scan/${scan.scanId}`)}
                      style={[styles.scanRow, idx < scans.length - 1 && styles.scanRowBorder]}
                    >
                      <View style={{ flex: 1 }}>
                        <Text style={styles.scanId}>Scan #{scan.scanId.slice(0, 8).toUpperCase()}</Text>
                        <Text style={styles.scanDate}>{new Date(scan.createdAt).toLocaleString("en-IN")}</Text>
                      </View>
                      <View style={styles.scanRight}>
                        <View style={[styles.badge, { backgroundColor: st.bg }]}>
                          <Text style={[styles.badgeText, { color: st.fg }]}>{st.label}</Text>
                        </View>
                        {typeof scan.score === "number" && <Text style={styles.scanScore}>{scan.score}%</Text>}
                      </View>
                    </Pressable>
                  );
                })
              )}
            </View>
          </View>
        </View>
      </View>

      <GovFooter />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { paddingBottom: 0 },
  inner: { padding: 16 },
  innerDesktop: { maxWidth: 1100, width: "100%", alignSelf: "center" },

  heroCard: {
    backgroundColor: colors.surface, borderRadius: 8, padding: 18, borderWidth: 1, borderColor: colors.border,
    borderLeftWidth: 5, borderLeftColor: gov.saffron, marginBottom: 20,
  },
  heroTitle: { fontSize: 20, fontWeight: "800", color: gov.navy },
  heroSub: { fontSize: 13, color: colors.muted, marginTop: 6, lineHeight: 19 },
  heroActions: { marginTop: 16, gap: 10 },
  heroActionsWide: { flexDirection: "row" },
  actionBtn: { flex: 1, borderColor: gov.navy },
  bigBtn: { paddingVertical: 6 },

  sectionTitleRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10, marginTop: 4 },
  sectionBar: { width: 4, height: 18, backgroundColor: gov.saffron, borderRadius: 2 },
  sectionTitle: { fontSize: 16, fontWeight: "800", color: gov.navy, textTransform: "uppercase", letterSpacing: 0.4 },

  statsRow: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginBottom: 20 },
  statCard: {
    flexGrow: 1, flexBasis: 140, backgroundColor: colors.surface, borderRadius: 8, padding: 14,
    borderWidth: 1, borderColor: colors.border, borderTopWidth: 4, gap: 4,
  },
  statValue: { fontSize: 24, fontWeight: "800", color: colors.text },
  statLabel: { fontSize: 12, color: colors.muted, fontWeight: "600" },

  twoCol: { flexDirection: "row", gap: 16 },
  col: { flex: 1 },

  panel: { backgroundColor: colors.surface, borderRadius: 8, borderWidth: 1, borderColor: colors.border, padding: 14, marginBottom: 20 },
  declRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: "#f1f5f9" },
  declText: { flex: 1, fontSize: 14, fontWeight: "600", color: colors.text },
  declFoot: { fontSize: 11, color: colors.muted, marginTop: 10, fontStyle: "italic" },

  noticePanel: { backgroundColor: "#fffbeb", borderColor: "#fde68a" },
  noticeRow: { flexDirection: "row", gap: 8, paddingVertical: 5 },
  noticeBullet: { color: colors.warning, fontWeight: "800" },
  noticeText: { flex: 1, fontSize: 13, color: "#78350f", lineHeight: 19 },

  recentHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  viewAll: { color: gov.navy, fontWeight: "700", fontSize: 13, marginBottom: 10 },
  scanRow: { flexDirection: "row", alignItems: "center", paddingVertical: 12 },
  scanRowBorder: { borderBottomWidth: 1, borderBottomColor: "#f1f5f9" },
  scanId: { fontSize: 14, fontWeight: "700", color: colors.text },
  scanDate: { fontSize: 12, color: colors.muted, marginTop: 2 },
  scanRight: { alignItems: "flex-end", gap: 4 },
  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  badgeText: { fontSize: 11, fontWeight: "700" },
  scanScore: { fontSize: 13, fontWeight: "700", color: colors.text },
  emptyText: { textAlign: "center", color: colors.muted, paddingVertical: 20 },
  errorText: { textAlign: "center", color: colors.danger, paddingVertical: 20 },
});