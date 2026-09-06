import React, { useState } from "react";
import { View, Text, StyleSheet, FlatList } from "react-native";
import { Card, ActivityIndicator, Chip, Searchbar } from "react-native-paper";
import { useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { ScanListItem } from "../../lib/types";

const statusColors: Record<string, string> = {
  created: "#9ca3af",
  uploading: "#60a5fa",
  queued: "#fbbf24",
  processing: "#f59e0b",
  done: "#22c55e",
  failed: "#ef4444",
};

export default function HistoryScreen() {
  const router = useRouter();
  const [search, setSearch] = useState("");

  const { data: scans, isLoading } = useQuery({
    queryKey: ["scans", "history"],
    queryFn: () => api.listScans({ page: 1, pageSize: 50 }),
  });

  const filtered = (scans || []).filter((s: ScanListItem) =>
    s.scanId.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Scan History</Text>
      <Searchbar placeholder="Search by scan ID" value={search} onChangeText={setSearch} style={styles.search} />

      {isLoading ? (
        <ActivityIndicator style={{ marginTop: 20 }} />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.scanId}
          contentContainerStyle={styles.listContent}
          renderItem={({ item }) => (
            <Card style={styles.card} onPress={() => router.push(`/scan/${item.scanId}`)}>
              <Card.Content style={styles.cardContent}>
                <View>
                  <Text style={styles.scanId}>#{item.scanId.slice(0, 8)}</Text>
                  <Text style={styles.date}>{new Date(item.createdAt).toLocaleString()}</Text>
                </View>
                <View style={styles.right}>
                  <Chip style={{ backgroundColor: statusColors[item.status] || "#9ca3af" }} textStyle={styles.chipText}>
                    {item.status}
                  </Chip>
                  {item.score !== undefined && <Text style={styles.score}>{item.score}%</Text>}
                </View>
              </Card.Content>
            </Card>
          )}
          ListEmptyComponent={<Text style={styles.emptyText}>No scans found.</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff", padding: 16 },
  heading: { fontSize: 22, fontWeight: "700", marginBottom: 12 },
  search: { marginBottom: 12 },
  listContent: { paddingBottom: 20 },
  card: { marginBottom: 10 },
  cardContent: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  scanId: { fontWeight: "600", fontSize: 15 },
  date: { fontSize: 12, color: "#999", marginTop: 2 },
  right: { alignItems: "flex-end", gap: 4 },
  chipText: { color: "#fff", fontSize: 11, textTransform: "capitalize" },
  score: { fontSize: 12, color: "#666" },
  emptyText: { textAlign: "center", color: "#999", marginTop: 40 },
});