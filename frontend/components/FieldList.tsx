import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Card, Chip, Divider } from "react-native-paper";
import type { ExtractedField } from "../lib/types";

interface FieldListProps {
  fields: ExtractedField[];
  onFieldPress?: (field: ExtractedField) => void;
}

function confidenceColor(confidence: number) {
  if (confidence >= 0.8) return "#22c55e";
  if (confidence >= 0.5) return "#f59e0b";
  return "#ef4444";
}

export default function FieldList({ fields, onFieldPress }: FieldListProps) {
  if (!fields || fields.length === 0) {
    return (
      <Card style={styles.emptyCard}>
        <Card.Content>
          <Text style={styles.emptyText}>No fields extracted yet.</Text>
        </Card.Content>
      </Card>
    );
  }

  return (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.title}>Extracted Fields</Text>
        {fields.map((field, idx) => (
          <View key={`${field.name}-${idx}`}>
            <View style={styles.row} onTouchEnd={() => onFieldPress?.(field)}>
              <View style={styles.rowLeft}>
                <Text style={styles.fieldName}>{field.name}</Text>
                <Text style={styles.fieldValue}>{field.value || "—"}</Text>
                <Text style={styles.fieldMeta}>Panel: {field.panelType}</Text>
              </View>
              <Chip
                style={[styles.confChip, { backgroundColor: confidenceColor(field.confidence) }]}
                textStyle={styles.confChipText}
              >
                {Math.round((field.confidence || 0) * 100)}%
              </Chip>
            </View>
            {idx < fields.length - 1 && <Divider style={styles.divider} />}
          </View>
        ))}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: 16 },
  emptyCard: { marginBottom: 16 },
  emptyText: { color: "#666", textAlign: "center" },
  title: { fontSize: 18, fontWeight: "700", marginBottom: 12 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 10 },
  rowLeft: { flex: 1 },
  fieldName: { fontSize: 12, color: "#666", textTransform: "uppercase" },
  fieldValue: { fontSize: 16, fontWeight: "600", marginTop: 2 },
  fieldMeta: { fontSize: 11, color: "#999", marginTop: 2 },
  confChip: { height: 28 },
  confChipText: { color: "#fff", fontSize: 11 },
  divider: { marginVertical: 2 },
});