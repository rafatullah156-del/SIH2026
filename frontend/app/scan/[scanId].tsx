import React, { useState } from "react";
import { View, Text, StyleSheet, ScrollView, Linking, Platform } from "react-native";
import { Button, ActivityIndicator, Modal, Portal, IconButton } from "react-native-paper";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useBreakpoint } from "../../lib/breakpoints";
import FieldList from "../../components/FieldList";
import ViolationList from "../../components/ViolationList";
import EvidenceViewer from "../../components/EvidenceViewer";
import type { Violation, ExtractedField, ScanImage } from "../../lib/types";

function scoreColor(score: number) {
  if (score >= 80) return "#22c55e";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}

export default function ScanDetailScreen() {
  const { scanId } = useLocalSearchParams<{ scanId: string }>();
  const router = useRouter();
  const { isDesktop, isTablet } = useBreakpoint();

  const [evidenceItem, setEvidenceItem] = useState<{ image: ScanImage | undefined; bbox: any; title: string } | null>(null);

  const { data: scan, isLoading, error } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => api.getScan(scanId as string),
    enabled: !!scanId,
  });

  const findImage = (imageId: string): ScanImage | undefined => scan?.images.find((im) => im.imageId === imageId);

  const handleViewFieldEvidence = (field: ExtractedField) => {
    setEvidenceItem({ image: findImage(field.imageId), bbox: field.bbox, title: field.name });
  };

  const handleViewViolationEvidence = (violation: Violation) => {
    setEvidenceItem({ image: findImage(violation.imageId), bbox: violation.bbox, title: violation.message });
  };

  const downloadPdf = () => {
    const url = scan?.report?.pdfUrl || api.getReportPdfUrl(scanId as string);
    if (Platform.OS === "web") {
      window.open(url, "_blank");
    } else {
      Linking.openURL(url);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error || !scan) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>Failed to load scan results.</Text>
        <Button mode="outlined" onPress={() => router.back()}>
          Go Back
        </Button>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={[styles.content, isDesktop && styles.contentDesktop]}>
      <View style={styles.header}>
        <Text style={styles.scanIdText}>Scan #{scan.scanId.slice(0, 8)}</Text>
        <Text style={styles.dateText}>{new Date(scan.createdAt).toLocaleString()}</Text>
      </View>

      {scan.score !== undefined && (
        <View style={[styles.scoreCard, { borderColor: scoreColor(scan.score) }]}>
          <Text style={styles.scoreLabel}>Compliance Score</Text>
          <Text style={[styles.scoreValue, { color: scoreColor(scan.score) }]}>{scan.score}%</Text>
        </View>
      )}

      <View style={isTablet || isDesktop ? styles.twoColumn : undefined}>
        <View style={isTablet || isDesktop ? styles.column : undefined}>
          <FieldList fields={scan.fields || []} onFieldPress={handleViewFieldEvidence} />
        </View>
        <View style={isTablet || isDesktop ? styles.column : undefined}>
          <ViolationList violations={scan.violations || []} onViewEvidence={handleViewViolationEvidence} />
        </View>
      </View>

      <View style={styles.reportRow}>
        <Button mode="contained" icon="file-pdf-box" onPress={downloadPdf}>
          Download PDF Report
        </Button>
      </View>

      <Portal>
        <Modal visible={!!evidenceItem} onDismiss={() => setEvidenceItem(null)} contentContainerStyle={styles.evidenceModal}>
          <View style={styles.evidenceHeader}>
            <Text style={styles.evidenceTitle}>{evidenceItem?.title}</Text>
            <IconButton icon="close" onPress={() => setEvidenceItem(null)} />
          </View>
          {evidenceItem?.image ? (
            <EvidenceViewer
              imageUrl={evidenceItem.image.viewUrl}
              originalWidth={evidenceItem.image.width}
              originalHeight={evidenceItem.image.height}
              bbox={evidenceItem.bbox}
            />
          ) : (
            <Text style={styles.noImageText}>Image not available</Text>
          )}
        </Modal>
      </Portal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  content: { padding: 16, paddingBottom: 40 },
  contentDesktop: { maxWidth: 1000, alignSelf: "center", width: "100%" },
  centerContainer: { flex: 1, justifyContent: "center", alignItems: "center", padding: 24 },
  errorText: { color: "#dc2626", marginBottom: 16 },
  header: { marginBottom: 16 },
  scanIdText: { fontSize: 20, fontWeight: "700" },
  dateText: { fontSize: 13, color: "#999", marginTop: 2 },
  scoreCard: { borderWidth: 2, borderRadius: 12, padding: 20, alignItems: "center", marginBottom: 20 },
  scoreLabel: { fontSize: 13, color: "#666", marginBottom: 4 },
  scoreValue: { fontSize: 36, fontWeight: "800" },
  twoColumn: { flexDirection: "row", gap: 16 },
  column: { flex: 1 },
  reportRow: { marginTop: 8, alignItems: "flex-start" },
  evidenceModal: { backgroundColor: "#fff", margin: 20, borderRadius: 12, padding: 16, maxHeight: "80%" },
  evidenceHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  evidenceTitle: { fontSize: 16, fontWeight: "700", flex: 1 },
  noImageText: { textAlign: "center", color: "#999", padding: 40 },
});