import React, { useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Modal, ActivityIndicator } from "react-native";
import { Button } from "react-native-paper";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter, useLocalSearchParams } from "expo-router";
import QRCode from "react-native-qrcode-svg";
import { api, errorToString } from "../../lib/api";
import { useBreakpoint } from "../../lib/breakpoints";
import CapturePanel from "../../components/CapturePanel";
import UploadProgress from "../../components/UploadProgress";
import { colors, gov } from "../../constants/theme";
import type { UploadFile, PairTokenResponse } from "../../lib/types";

export default function NewScanScreen() {
  const router = useRouter();
  const { qr } = useLocalSearchParams<{ qr?: string }>();
  const { isDesktop } = useBreakpoint();

  // ---------- Scan state ----------
  const [scanId, setScanId] = useState<string | null>(null);
  const [front, setFront] = useState<UploadFile | null>(null);
  const [back, setBack] = useState<UploadFile | null>(null);
  const [calibration, setCalibration] = useState<UploadFile | null>(null);

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // ---------- QR pairing state ----------
  const [qrModalVisible, setQrModalVisible] = useState(false);
  const [pairToken, setPairToken] = useState<PairTokenResponse | null>(null);
  const [qrLoading, setQrLoading] = useState(false);
  const [waitingForPhone, setWaitingForPhone] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopTimers = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
    pollRef.current = null;
    countdownRef.current = null;
  };

  // ---------- Poll backend until phone has uploaded ----------
  const pollForScanStart = (id: string, expiresAt: string) => {
    stopTimers();
    setWaitingForPhone(true);

    const expireTime = new Date(expiresAt).getTime();

    countdownRef.current = setInterval(() => {
      const left = Math.max(0, Math.floor((expireTime - Date.now()) / 1000));
      setSecondsLeft(left);
    }, 1000);

    pollRef.current = setInterval(async () => {
      if (Date.now() > expireTime) {
        stopTimers();
        setWaitingForPhone(false);
        setQrModalVisible(false);
        setPairToken(null);
        setError("QR code expired. Please generate a new one.");
        return;
      }
      try {
        const scan = await api.getScan(id);
        if (["queued", "processing", "done"].includes(scan.status)) {
          stopTimers();
          setWaitingForPhone(false);
          setQrModalVisible(false);
          router.replace(`/scan/processing?scanId=${id}`);
        }
      } catch {
        // ignore transient network errors while polling
      }
    }, 2500);
  };

  // ---------- Generate token + open QR modal ----------
  const startQrFlow = async (id: string) => {
    setQrLoading(true);
    setError(null);
    try {
      const data = await api.createPairToken(id);
      setPairToken(data);
      setQrModalVisible(true);
      pollForScanStart(id, data.expiresAt);
    } catch (e: any) {
      setError(errorToString(e));
    } finally {
      setQrLoading(false);
    }
  };

  // ---------- Create scan on mount (and auto-open QR if ?qr=1) ----------
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const id = await api.createScan();
        if (cancelled) return;
        setScanId(id);
        if (qr === "1") {
          await startQrFlow(id);
        }
      } catch (e: any) {
        if (!cancelled) setError(errorToString(e) || "Failed to create scan");
      }
    })();
    return () => {
      cancelled = true;
      stopTimers();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------- Upload + submit ----------
  const canSubmit = !!front && !!back && !!scanId && !uploading;

  const handleSubmit = async () => {
    if (!scanId || !front || !back) return;
    setUploading(true);
    setError(null);
    try {
      setUploadProgress(0.1);
      await api.uploadScanImage(scanId, "front", front);
      setUploadProgress(0.4);
      await api.uploadScanImage(scanId, "back", back);
      setUploadProgress(0.7);
      if (calibration) {
        await api.uploadScanImage(scanId, "calibration", calibration);
      }
      setUploadProgress(0.9);
      await api.submitScan(scanId);
      setUploadProgress(1);
      router.replace(`/scan/processing?scanId=${scanId}`);
    } catch (e: any) {
      setError(errorToString(e) || "Upload failed. Please retry.");
    } finally {
      setUploading(false);
    }
  };

  const openQrFlow = () => {
    if (!scanId) return;
    startQrFlow(scanId);
  };

  const closeQrModal = () => {
    stopTimers();
    setWaitingForPhone(false);
    setQrModalVisible(false);
  };

  const formatTime = (s: number) =>
    `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  return (
    <ScrollView style={styles.container} contentContainerStyle={[styles.content, isDesktop && styles.contentDesktop]}>
      {/* Header card */}
      <View style={styles.headerCard}>
        <View style={{ flex: 1 }}>
          <Text style={styles.heading}>New Compliance Scan</Text>
          <Text style={styles.subheading}>
            Capture the front and back panels of the package label. Add a calibration image to enable font-size checks.
          </Text>
        </View>
        {scanId && (
          <View style={styles.idPill}>
            <Text style={styles.idPillLabel}>Scan ID</Text>
            <Text style={styles.idPillValue}>{scanId.slice(0, 8).toUpperCase()}</Text>
          </View>
        )}
      </View>

      {/* Error */}
      {error ? (
        <View style={styles.errorBox}>
          <MaterialCommunityIcons name="alert-circle" size={18} color={colors.danger} />
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {/* Capture panels */}
      <CapturePanel label="Front Panel" required file={front} onChange={setFront} />
      <CapturePanel label="Back Panel" required file={back} onChange={setBack} />
      <CapturePanel label="Calibration Image (for font-size check)" file={calibration} onChange={setCalibration} />

      {/* Upload progress */}
      {uploading && <UploadProgress progress={uploadProgress} label="Uploading images & submitting for analysis..." />}

      {/* Submit */}
      <Button
        mode="contained"
        icon="send-check"
        onPress={handleSubmit}
        disabled={!canSubmit}
        loading={uploading}
        buttonColor={canSubmit ? gov.navy : undefined}
        style={styles.submitBtn}
        contentStyle={styles.btnContent}
      >
        Submit for Compliance Check
      </Button>

      {!front || !back ? (
        <Text style={styles.submitHint}>Add the Front and Back panel images to enable submission.</Text>
      ) : null}

      <View style={styles.dividerRow}>
        <View style={styles.dividerLine} />
        <Text style={styles.dividerText}>OR</Text>
        <View style={styles.dividerLine} />
      </View>

      <Button
        mode="outlined"
        icon="qrcode-scan"
        onPress={openQrFlow}
        disabled={!scanId || qrLoading || uploading}
        loading={qrLoading}
        style={styles.qrBtn}
        contentStyle={styles.btnContent}
        textColor={gov.navy}
      >
        Use Phone Camera (Scan QR)
      </Button>
      <Text style={styles.qrHint}>
        Recommended on laptops: capture higher-quality images using your mobile phone. The QR code is valid for one-time use only.
      </Text>

      {/* QR Modal */}
      <Modal visible={qrModalVisible} transparent animationType="fade" onRequestClose={closeQrModal}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <View style={styles.modalTricolor}>
              <View style={[styles.stripe, { backgroundColor: gov.saffron }]} />
              <View style={[styles.stripe, { backgroundColor: gov.white }]} />
              <View style={[styles.stripe, { backgroundColor: gov.green }]} />
            </View>

            <Text style={styles.modalTitle}>Scan with your Phone</Text>
            <Text style={styles.modalSub}>Open your phone camera and point it at this code</Text>

            {pairToken && (
              <View style={styles.qrWrap}>
                <QRCode value={pairToken.joinUrl} size={220} color={gov.navyDark} backgroundColor="#ffffff" />
              </View>
            )}

            {secondsLeft !== null && (
              <View style={[styles.timerPill, secondsLeft < 60 && styles.timerPillWarn]}>
                <MaterialCommunityIcons name="timer-outline" size={14} color={secondsLeft < 60 ? colors.danger : gov.navy} />
                <Text style={[styles.timerText, secondsLeft < 60 && { color: colors.danger }]}>
                  Expires in {formatTime(secondsLeft)}
                </Text>
              </View>
            )}

            {waitingForPhone && (
              <View style={styles.waitingRow}>
                <ActivityIndicator size="small" color={gov.navy} />
                <Text style={styles.waitingText}>Waiting for upload from phone…</Text>
              </View>
            )}

            <Text style={styles.modalNote}>
              This QR is single-use. After the phone sends images, it becomes invalid automatically.
            </Text>

            <Button mode="text" onPress={closeQrModal} textColor={colors.muted} style={styles.closeBtn}>
              Cancel
            </Button>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: 16, paddingBottom: 40 },
  contentDesktop: { maxWidth: 760, alignSelf: "center", width: "100%" },

  headerCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    backgroundColor: colors.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    borderLeftWidth: 5,
    borderLeftColor: gov.saffron,
    padding: 16,
    marginBottom: 18,
  },
  heading: { fontSize: 20, fontWeight: "800", color: gov.navy },
  subheading: { fontSize: 13, color: colors.muted, marginTop: 6, lineHeight: 19 },
  idPill: { backgroundColor: "#eef2f7", borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, alignItems: "center" },
  idPillLabel: { fontSize: 10, color: colors.muted, fontWeight: "600", textTransform: "uppercase" },
  idPillValue: { fontSize: 13, fontWeight: "800", color: gov.navy, letterSpacing: 0.5 },

  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.dangerBg,
    borderColor: colors.danger,
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  errorText: { flex: 1, color: colors.danger, fontSize: 13, fontWeight: "600" },

  submitBtn: { marginTop: 8 },
  submitHint: { fontSize: 12, color: colors.muted, marginTop: 8, textAlign: "center" },
  btnContent: { paddingVertical: 6 },

  dividerRow: { flexDirection: "row", alignItems: "center", gap: 10, marginVertical: 16 },
  dividerLine: { flex: 1, height: 1, backgroundColor: colors.border },
  dividerText: { fontSize: 12, fontWeight: "700", color: colors.muted },

  qrBtn: { borderColor: gov.navy, borderWidth: 1.5 },
  qrHint: { fontSize: 12, color: colors.muted, marginTop: 8, lineHeight: 17, textAlign: "center" },

  modalOverlay: { flex: 1, backgroundColor: "rgba(7,28,61,0.7)", justifyContent: "center", alignItems: "center", padding: 16 },
  modalBox: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 24,
    width: "100%",
    maxWidth: 380,
    alignItems: "center",
    overflow: "hidden",
  },
  modalTricolor: { position: "absolute", top: 0, left: 0, right: 0, flexDirection: "row", height: 5 },
  stripe: { flex: 1 },
  modalTitle: { fontSize: 18, fontWeight: "800", color: gov.navy, marginTop: 6 },
  modalSub: { fontSize: 13, color: colors.muted, marginTop: 4, marginBottom: 16, textAlign: "center" },
  qrWrap: { padding: 14, backgroundColor: "#fff", borderRadius: 10, borderWidth: 1, borderColor: colors.border, marginBottom: 14 },
  timerPill: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "#eef2f7", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 20, marginBottom: 10 },
  timerPillWarn: { backgroundColor: colors.dangerBg },
  timerText: { fontSize: 12, fontWeight: "700", color: gov.navy },
  waitingRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  waitingText: { fontSize: 13, color: colors.text, fontWeight: "600" },
  modalNote: { fontSize: 11, color: colors.muted, textAlign: "center", lineHeight: 16, marginBottom: 6 },
  closeBtn: { marginTop: 4 },
});