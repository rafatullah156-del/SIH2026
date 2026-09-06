import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { ProgressBar, useTheme } from "react-native-paper";

interface UploadProgressProps {
  progress: number;
  label?: string;
  status?: "uploading" | "success" | "error";
}

export default function UploadProgress({
  progress,
  label = "Uploading...",
  status = "uploading",
}: UploadProgressProps) {
  const theme = useTheme();

  const color =
    status === "success" ? "#22c55e" : status === "error" ? "#ef4444" : theme.colors.primary;

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <ProgressBar progress={progress} color={color} style={styles.bar} />
      <Text style={styles.percent}>{Math.round(progress * 100)}%</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginVertical: 8 },
  label: { fontSize: 14, marginBottom: 4 },
  bar: { height: 8, borderRadius: 4 },
  percent: { fontSize: 12, color: "#666", marginTop: 4, textAlign: "right" },
});