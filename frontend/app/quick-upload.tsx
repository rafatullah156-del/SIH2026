import React, { useState } from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";
import { Button } from "react-native-paper";
import { useLocalSearchParams } from "expo-router";
import { api, errorToString } from "../lib/api";
import CapturePanel from "../components/CapturePanel";
import UploadProgress from "../components/UploadProgress";
import { colors } from "../constants/theme";
import type { UploadFile } from "../lib/types";

type SubmitState = "idle" | "sending" | "success" | "error" | "invalid";

export default function QuickUploadScreen() {
  const { t } = useLocalSearchParams<{ t: string | string[] }>();

  const [front, setFront] = useState<UploadFile | null>(null);
  const [back, setBack] = useState<UploadFile | null>(null);
  const [calibration, setCalibration] = useState<UploadFile | null>(null);

  const [state, setState] = useState<SubmitState>("idle");
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const token = typeof t === "string" ? t : Array.isArray(t) ? t[0] : "";
  const canSend = !!front && !!back && !!token && state !== "sending";

  const handleSend = async () => {
    if (!token) {
      setState("invalid");
      setErrorMsg("Missing or invalid token in URL.");
      return;
    }
    if (!front || !back) return;

    setState("sending");
    setErrorMsg(null);
    setProgress(0.2);

    try {
      setProgress(0.5);
      await api.pairSubmit(token, {
        front,
        back,
        calibration: calibration || undefined,
      });
      setProgress(1);
      setState("success");
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 410) {
        setState("invalid");
        setErrorMsg("This QR code has expired. Please generate a new one on the laptop.");
      } else if (status === 409) {
        setState("invalid");
        setErrorMsg("This QR code has already been used.");
      } else {
        setState("error");
        setErrorMsg(errorToString(e));
      }
    }
  };

  // ---------- No token in URL ----------
  if (!token) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.invalidIcon}>⚠️</Text>
        <Text style={styles.invalidTitle}>Invalid Link</Text>
        <Text style={styles.invalidMessage}>
          No upload token found. Please scan the QR code again.
        </Text>
      </View>
    );
  }

  // ---------- Success ----------
  if (state === "success") {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.successIcon}>✅</Text>
        <Text style={styles.successTitle}>Images Sent!</Text>
        <Text style={styles.successMessage}>
          You can now go back to the laptop to view results. This link is no longer valid.
        </Text>
      </View>
    );
  }

  // ---------- Token expired / already used ----------
  if (state === "invalid") {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.invalidIcon}>⚠️</Text>
        <Text style={styles.invalidTitle}>Link Expired / Used</Text>
        <Text style={styles.invalidMessage}>{errorMsg}</Text>
      </View>
    );
  }

  // ---------- Capture form ----------
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Quick Upload</Text>
      <Text style={styles.subheading}>
        Capture the label images and send them to your laptop
      </Text>

      {errorMsg ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{errorMsg}</Text>
        </View>
      ) : null}

      <CapturePanel label="Front Image" required file={front} onChange={setFront} />
      <CapturePanel label="Back Image" required file={back} onChange={setBack} />
      <CapturePanel label="Calibration Image" file={calibration} onChange={setCalibration} />

      {state === "sending" && (
        <UploadProgress progress={progress} label="Sending images..." />
      )}

      <Button
        mode="contained"
        icon="send"
        onPress={handleSend}
        disabled={!canSend}
        loading={state === "sending"}
        style={styles.sendBtn}
        contentStyle={styles.sendBtnContent}
      >
        Send
      </Button>

      {state === "error" && (
        <Text style={styles.retryHint}>Fix the issue above and press Send again.</Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: 16, paddingBottom: 40 },
  heading: { fontSize: 22, fontWeight: "700", color: colors.text },
  subheading: { fontSize: 14, color: colors.muted, marginTop: 4, marginBottom: 20 },

  errorBox: {
    backgroundColor: colors.dangerBg,
    borderColor: colors.danger,
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  errorText: { color: colors.danger, fontSize: 13, fontWeight: "600" },

  sendBtn: { marginTop: 16 },
  sendBtnContent: { paddingVertical: 6 },
  retryHint: { marginTop: 10, fontSize: 12, color: colors.muted, textAlign: "center" },

  centerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
    backgroundColor: colors.background,
  },
  successIcon: { fontSize: 56, marginBottom: 16 },
  successTitle: { fontSize: 22, fontWeight: "700", color: colors.success, marginBottom: 8 },
  successMessage: { fontSize: 14, color: colors.muted, textAlign: "center" },
  invalidIcon: { fontSize: 56, marginBottom: 16 },
  invalidTitle: { fontSize: 20, fontWeight: "700", color: colors.danger, marginBottom: 8 },
  invalidMessage: { fontSize: 14, color: colors.muted, textAlign: "center" },
});