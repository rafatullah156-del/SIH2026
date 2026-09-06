import React, { useEffect } from "react";
import { View, Text, StyleSheet } from "react-native";
import { ActivityIndicator, Button } from "react-native-paper";
import { useRouter, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";

const statusMessages: Record<string, string> = {
  created: "Scan created...",
  uploading: "Uploading images...",
  queued: "Queued for processing...",
  processing: "Running OCR & compliance checks...",
  done: "Done!",
  failed: "Processing failed",
};

export default function ProcessingScreen() {
  const router = useRouter();
  const { scanId } = useLocalSearchParams<{ scanId: string }>();

  const { data: scan, error } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => api.getScan(scanId as string),
    enabled: !!scanId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "failed") return false;
      return 2000;
    },
  });

  useEffect(() => {
    if (scan?.status === "done") {
      router.replace(`/scan/${scanId}`);
    }
  }, [scan?.status]);

  const retry = async () => {
    if (!scanId) return;
    try {
      await api.submitScan(scanId as string);
    } catch {}
  };

  const status = scan?.status || "queued";
  const isFailed = status === "failed";

  return (
    <View style={styles.container}>
      {!isFailed ? (
        <>
          <ActivityIndicator size="large" style={styles.spinner} />
          <Text style={styles.status}>{statusMessages[status] || status}</Text>
          <Text style={styles.hint}>This may take a few moments...</Text>
        </>
      ) : (
        <>
          <Text style={styles.failedIcon}>⚠️</Text>
          <Text style={styles.failedTitle}>Processing Failed</Text>
          <Text style={styles.failedMessage}>{scan?.error || "Something went wrong."}</Text>
          <Button mode="contained" onPress={retry} style={styles.retryBtn}>
            Retry
          </Button>
          <Button mode="text" onPress={() => router.replace("/")}>
            Back to Home
          </Button>
        </>
      )}
      {error && <Text style={styles.errorText}>Connection error. Retrying...</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff", justifyContent: "center", alignItems: "center", padding: 24 },
  spinner: { marginBottom: 24 },
  status: { fontSize: 18, fontWeight: "600", marginBottom: 8 },
  hint: { fontSize: 13, color: "#999" },
  failedIcon: { fontSize: 48, marginBottom: 16 },
  failedTitle: { fontSize: 20, fontWeight: "700", color: "#dc2626", marginBottom: 8 },
  failedMessage: { fontSize: 14, color: "#666", textAlign: "center", marginBottom: 24 },
  retryBtn: { marginBottom: 8, minWidth: 160 },
  errorText: { marginTop: 16, fontSize: 12, color: "#f59e0b" },
});