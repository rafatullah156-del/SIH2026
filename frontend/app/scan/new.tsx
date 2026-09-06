import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Button, Chip, ProgressBar } from "react-native-paper";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter, useLocalSearchParams } from "expo-router";
import QRCode from "react-native-qrcode-svg";
import { api, errorToString } from "../../lib/api";
import { useBreakpoint } from "../../lib/breakpoints";
import CapturePanel from "../../components/CapturePanel";
import { colors, gov } from "../../constants/theme";
import type { PairTokenResponse, UploadFile } from "../../lib/types";

// ─── LMPC 2011 checklist shown to officer before scanning ───────────────────
const LMPC_CHECKLIST = [
  { key: "common_name", label: "Common/Generic Name", rule: "Rule 6(1)(b)", panel: "front" },
  { key: "mrp", label: "MRP (Incl. of all taxes)", rule: "Rule 6(1)(e)", panel: "front" },
  { key: "net_qty", label: "Net Quantity (SI units)", rule: "Rule 6(1)(c)", panel: "front" },
  { key: "mfd", label: "Month & Year of Mfg/Pkg", rule: "Rule 6(1)(d)", panel: "back" },
  { key: "manufacturer", label: "Manufacturer Name + Address + PIN", rule: "Rule 6(1)(a)", panel: "back" },
  { key: "consumer_care", label: "Consumer Care (Phone/Email)", rule: "Rule 6(1)(f)", panel: "back" },
  { key: "best_before", label: "Best Before / Expiry (food)", rule: "Rule 6(2)", panel: "back" },
  { key: "fssai", label: "FSSAI License No. (food)", rule: "FSS Act 2006", panel: "back" },
];

type UploadStep = "idle" | "uploading_front" | "uploading_back" | "uploading_cal" | "submitting" | "done";

export default function NewScanScreen() {
  const router = useRouter();
  const { qr } = useLocalSearchParams<{ qr?: string }>();
  const { isDesktop } = useBreakpoint();

  const [scanId, setScanId] = useState<string | null>(null);
  const [front, setFront] = useState<UploadFile | null>(null);
  const [back, setBack] = useState<UploadFile | null>(null);
  const [calibration, setCalibration] = useState<UploadFile | null>(null);

  const [uploadStep, setUploadStep] = useState<UploadStep>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [checklistVisible, setChecklistVisible] = useState(false);

  // QR pairing
  const [qrModalVisible, setQrModalVisible] = useState(false);
  const [pairToken, setPairToken] = useState<PairTokenResponse | null>(null);
  const [qrLoading, setQrLoading] = useState(false);
  const [waitingForPhone, setWaitingForPhone] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopTimers = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
    pollRef.current = null;
    countdownRef.current = null;
  }, []);

  const pollForScanStart = useCallback(
    (id: string, expiresAt: string) => {
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
        } catch { /* ignore transient */ }
      }, 2500);
    },
    [stopTimers, router],
  );

  const startQrFlow = useCallback(
    async (id: string) => {
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
    },
    [pollForScanStart],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const id = await api.createScan();
        if (cancelled) return;
        setScanId(id);
        if (qr === "1") await startQrFlow(id);
      } catch (e: any) {
        if (!cancelled) setError(errorToString(e) || "Failed to initialise scan");
      }
    })();
    return () => {
      cancelled = true;
      stopTimers();
    };
  }, []);

  // ─── Upload (parallel front+back, then calibration, then submit) ──────
  const canSubmit = !!front && !!back && !!scanId && uploadStep === "idle";

  const handleSubmit = async () => {
    if (!scanId || !front || !back) return;
    setError(null);
    try {
      // Upload front + back in PARALLEL
      setUploadStep("uploading_front");
      setUploadProgress(0.1);
      await Promise.all([
        api.uploadScanImage(scanId, "front", front).then(() => setUploadProgress(0.45)),
        api.uploadScanImage(scanId, "back", back).then(() => setUploadProgress(0.7)),
      ]);

      // Calibration if present
      if (calibration) {
        setUploadStep("uploading_cal");
        setUploadProgress(0.8);
        await api.uploadScanImage(scanId, "calibration", calibration);
      }

      setUploadStep("submitting");
      setUploadProgress(0.9);
      await api.submitScan(scanId);
      setUploadProgress(1.0);
      setUploadStep("done");
      router.replace(`/scan/processing?scanId=${scanId}`);
    } catch (e: any) {
      setError(errorToString(e) || "Upload failed. Please retry.");
      setUploadStep("idle");
    }
  };

  const uploading = uploadStep !== "idle" && uploadStep !== "done";

  const stepLabel: Record<UploadStep, string> = {
    idle: "",
    uploading_front: "Uploading front panel…",
    uploading_back: "Uploading back panel…",
    uploading_cal: "Uploading calibration image…",
    submitting: "Submitting for compliance check…",
    done: "Submitted! Redirecting…",
  };

  const formatTime = (s: number) =>
    `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, isDesktop && styles.contentDesktop]}
    >
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <View style={styles.headerCard}>
        <View style={styles.tricolorBar}>
          <View style={[styles.stripe, { backgroundColor: gov.saffron }]} />
          <View style={[styles.stripe, { backgroundColor: gov.white, borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#ddd" }]} />
          <View style={[styles.stripe, { backgroundColor: gov.green }]} />
        </View>
        <View style={styles.headerBody}>
          <View style={{ flex: 1 }}>
            <Text style={styles.heading}>LM(PC) Compliance Scan</Text>
            <Text style={styles.subheading}>
              Ministry of Consumer Affairs, Food & Public Distribution{"\n"}
              Legal Metrology (Packaged Commodities) Rules, 2011
            </Text>
          </View>
          {scanId && (
            <View style={styles.idPill}>
              <Text style={styles.idPillLabel}>Scan ID</Text>
              <Text style={styles.idPillValue}>{scanId.slice(0, 8).toUpperCase()}</Text>
            </View>
          )}
        </View>
      </View>

      {/* ── LMPC Quick Reference ────────────────────────────────────────── */}
      <TouchableOpacity
        style={styles.checklistToggle}
        onPress={() => setChecklistVisible((v) => !v)}
        activeOpacity={0.8}
      >
        <MaterialCommunityIcons
          name="clipboard-check-outline"
          size={18}
          color={gov.navy}
        />
        <Text style={styles.checklistToggleText}>
          LMPC 2011 — Mandatory Declarations Checklist
        </Text>
        <MaterialCommunityIcons
          name={checklistVisible ? "chevron-up" : "chevron-down"}
          size={18}
          color={gov.navy}
        />
      </TouchableOpacity>

      {checklistVisible && (
        <View style={styles.checklistBox}>
          <Text style={styles.checklistNote}>
            Verify these declarations are present on the label before scanning:
          </Text>
          {LMPC_CHECKLIST.map((item) => (
            <View key={item.key} style={styles.checklistRow}>
              <MaterialCommunityIcons
                name="checkbox-blank-circle-outline"
                size={14}
                color={gov.navy}
              />
              <View style={{ flex: 1 }}>
                <Text style={styles.checklistLabel}>{item.label}</Text>
                <Text style={styles.checklistMeta}>
                  {item.rule} · {item.panel} panel
                </Text>
              </View>
            </View>
          ))}
          <View style={styles.checklistFooter}>
            <MaterialCommunityIcons name="information-outline" size={13} color={colors.muted} />
            <Text style={styles.checklistFooterText}>
              AI will automatically check all these + font size, placement, date format, dual MRP, tax wording
            </Text>
          </View>
        </View>
      )}

      {/* ── Error ────────────────────────────────────────────────────────── */}
      {error ? (
        <View style={styles.errorBox}>
          <MaterialCommunityIcons name="alert-circle" size={18} color={colors.danger} />
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {/* ── Capture Panels ────────────────────────────────────────────────── */}
      <View style={styles.sectionHeader}>
        <MaterialCommunityIcons name="camera" size={16} color={gov.navy} />
        <Text style={styles.sectionTitle}>Step 1: Capture Label Images</Text>
      </View>

      <CapturePanel
        label="Front Panel"
        hint="Must show: Product name, MRP, Net Quantity"
        required
        file={front}
        onChange={setFront}
      />
      <CapturePanel
        label="Back Panel"
        hint="Must show: Manufacturer address, MFD date, Consumer care, FSSAI"
        required
        file={back}
        onChange={setBack}
      />
      <CapturePanel
        label="Calibration Image (Optional)"
        hint="Place a standard ruler or A4 paper next to the label. Enables font-size verification per Rule 8."
        file={calibration}
        onChange={setCalibration}
      />

      {/* ── Upload Progress ─────────────────────────────────────────────── */}
      {uploading && (
        <View style={styles.progressBox}>
          <View style={styles.progressHeader}>
            <ActivityIndicator size="small" color={gov.navy} />
            <Text style={styles.progressLabel}>{stepLabel[uploadStep]}</Text>
          </View>
          <ProgressBar
            progress={uploadProgress}
            color={gov.navy}
            style={styles.progressBar}
          />
          <Text style={styles.progressPct}>{Math.round(uploadProgress * 100)}%</Text>
        </View>
      )}

      {/* ── Submit ─────────────────────────────────────────────────────── */}
      <View style={styles.sectionHeader}>
        <MaterialCommunityIcons name="send-check" size={16} color={gov.navy} />
        <Text style={styles.sectionTitle}>Step 2: Submit for Analysis</Text>
      </View>

      <View style={styles.whatWeCheckBox}>
        <Text style={styles.whatWeCheckTitle}>What our AI checks:</Text>
        {[
          "✓ Presence of all 6 mandatory Rule 6 declarations",
          "✓ MRP format + 'Inclusive of all taxes' wording",
          "✓ Dual MRP detection (prohibited)",
          "✓ Date format validation (Month-Year only)",
          "✓ Manufacturer complete address + PIN",
          "✓ Standard pack size (Schedule II)",
          "✓ Font size of net quantity (Rule 8) if calibration given",
          "✓ Placement on Principal Display Panel (Rule 7)",
          "✓ Best before for food products",
          "✓ FSSAI license number (14 digits)",
          "✓ Country of origin for imports",
          "✓ E-commerce declarations (Rule 18)",
        ].map((line, i) => (
          <Text key={i} style={styles.whatWeCheckItem}>{line}</Text>
        ))}
      </View>

      <Button
        mode="contained"
        icon="shield-check"
        onPress={handleSubmit}
        disabled={!canSubmit}
        loading={uploading}
        buttonColor={canSubmit ? gov.navy : undefined}
        style={styles.submitBtn}
        contentStyle={styles.btnContent}
      >
        Run Compliance Check
      </Button>

      {(!front || !back) && (
        <Text style={styles.submitHint}>
          Add Front and Back panel images to enable submission.
        </Text>
      )}

      {/* ── OR divider ──────────────────────────────────────────────────── */}
      <View style={styles.dividerRow}>
        <View style={styles.dividerLine} />
        <Text style={styles.dividerText}>OR USE PHONE CAMERA</Text>
        <View style={styles.dividerLine} />
      </View>

      <Button
        mode="outlined"
        icon="qrcode-scan"
        onPress={() => scanId && startQrFlow(scanId)}
        disabled={!scanId || qrLoading || uploading}
        loading={qrLoading}
        style={styles.qrBtn}
        contentStyle={styles.btnContent}
        textColor={gov.navy}
      >
        Scan QR with Phone Camera
      </Button>
      <Text style={styles.qrHint}>
        Better image quality on phone camera → more accurate OCR → fewer false negatives.
        Token is one-time use, expires in 10 minutes.
      </Text>

      {/* ── QR Modal ───────────────────────────────────────────────────── */}
      <Modal
        visible={qrModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => {
          stopTimers();
          setQrModalVisible(false);
        }}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <View style={styles.modalTricolor}>
              <View style={[styles.stripe, { backgroundColor: gov.saffron }]} />
              <View style={[styles.stripe, { backgroundColor: gov.white }]} />
              <View style={[styles.stripe, { backgroundColor: gov.green }]} />
            </View>

            <Text style={styles.modalTitle}>📱 Scan with Phone</Text>
            <Text style={styles.modalSub}>
              Point your phone camera at this QR code
            </Text>

            {pairToken && (
              <View style={styles.qrWrap}>
                <QRCode
                  value={pairToken.joinUrl}
                  size={220}
                  color={gov.navyDark ?? gov.navy}
                  backgroundColor="#ffffff"
                />
              </View>
            )}

            {secondsLeft !== null && (
              <View style={[styles.timerPill, secondsLeft < 60 && styles.timerPillWarn]}>
                <MaterialCommunityIcons
                  name="timer-outline"
                  size={14}
                  color={secondsLeft < 60 ? colors.danger : gov.navy}
                />
                <Text style={[styles.timerText, secondsLeft < 60 && { color: colors.danger }]}>
                  Expires in {formatTime(secondsLeft)}
                </Text>
              </View>
            )}

            {waitingForPhone && (
              <View style={styles.waitingRow}>
                <ActivityIndicator size="small" color={gov.navy} />
                <Text style={styles.waitingText}>Waiting for images from phone…</Text>
              </View>
            )}

            <View style={styles.modalSteps}>
              {["Open phone camera", "Scan QR code", "Capture front + back panels", "Tap Send → done!"].map(
                (step, i) => (
                  <View key={i} style={styles.modalStepRow}>
                    <View style={styles.stepNum}>
                      <Text style={styles.stepNumText}>{i + 1}</Text>
                    </View>
                    <Text style={styles.stepText}>{step}</Text>
                  </View>
                ),
              )}
            </View>

            <Text style={styles.modalNote}>
              🔒 Single-use token. Automatically invalidated after phone submits.
            </Text>

            <Button
              mode="text"
              onPress={() => {
                stopTimers();
                setWaitingForPhone(false);
                setQrModalVisible(false);
              }}
              textColor={colors.muted}
            >
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
  content: { padding: 16, paddingBottom: 48 },
  contentDesktop: { maxWidth: 780, alignSelf: "center", width: "100%" },

  headerCard: {
    borderRadius: 10,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 16,
  },
  tricolorBar: { flexDirection: "row", height: 6 },
  stripe: { flex: 1 },
  headerBody: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    backgroundColor: colors.surface,
    padding: 16,
  },
  heading: { fontSize: 18, fontWeight: "800", color: gov.navy },
  subheading: { fontSize: 12, color: colors.muted, marginTop: 4, lineHeight: 18 },
  idPill: {
    backgroundColor: "#eef2f7",
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    alignItems: "center",
  },
  idPillLabel: { fontSize: 9, color: colors.muted, fontWeight: "700", textTransform: "uppercase" },
  idPillValue: { fontSize: 13, fontWeight: "800", color: gov.navy },

  checklistToggle: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#EEF4FF",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#C7D9F8",
    padding: 12,
    marginBottom: 8,
  },
  checklistToggleText: { flex: 1, fontSize: 13, fontWeight: "700", color: gov.navy },
  checklistBox: {
    backgroundColor: "#F8FAFF",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#C7D9F8",
    padding: 14,
    marginBottom: 16,
  },
  checklistNote: { fontSize: 12, color: colors.muted, marginBottom: 10, fontStyle: "italic" },
  checklistRow: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 8 },
  checklistLabel: { fontSize: 13, fontWeight: "600", color: colors.text },
  checklistMeta: { fontSize: 11, color: colors.muted, marginTop: 1 },
  checklistFooter: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderColor: "#C7D9F8",
  },
  checklistFooterText: { flex: 1, fontSize: 11, color: colors.muted, lineHeight: 16 },

  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#FEF2F2",
    borderColor: colors.danger,
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  errorText: { flex: 1, color: colors.danger, fontSize: 13, fontWeight: "600" },

  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
    marginTop: 8,
  },
  sectionTitle: { fontSize: 14, fontWeight: "700", color: gov.navy },

  progressBox: {
    backgroundColor: "#EEF4FF",
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#C7D9F8",
  },
  progressHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  progressLabel: { fontSize: 13, color: gov.navy, fontWeight: "600" },
  progressBar: { borderRadius: 4, height: 6 },
  progressPct: { fontSize: 11, color: colors.muted, textAlign: "right", marginTop: 4 },

  whatWeCheckBox: {
    backgroundColor: "#F0FDF4",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#BBF7D0",
    padding: 14,
    marginBottom: 14,
  },
  whatWeCheckTitle: { fontSize: 13, fontWeight: "700", color: "#166534", marginBottom: 8 },
  whatWeCheckItem: { fontSize: 12, color: "#15803D", lineHeight: 20 },

  submitBtn: { marginTop: 4 },
  submitHint: { fontSize: 12, color: colors.muted, marginTop: 8, textAlign: "center" },
  btnContent: { paddingVertical: 6 },

  dividerRow: { flexDirection: "row", alignItems: "center", gap: 10, marginVertical: 20 },
  dividerLine: { flex: 1, height: 1, backgroundColor: colors.border },
  dividerText: { fontSize: 10, fontWeight: "700", color: colors.muted, letterSpacing: 0.5 },

  qrBtn: { borderColor: gov.navy, borderWidth: 1.5 },
  qrHint: { fontSize: 12, color: colors.muted, marginTop: 8, lineHeight: 17, textAlign: "center" },

  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(7,28,61,0.75)",
    justifyContent: "center",
    alignItems: "center",
    padding: 16,
  },
  modalBox: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 24,
    width: "100%",
    maxWidth: 380,
    alignItems: "center",
    overflow: "hidden",
  },
  modalTricolor: { position: "absolute", top: 0, left: 0, right: 0, flexDirection: "row", height: 5 },
  modalTitle: { fontSize: 20, fontWeight: "800", color: gov.navy, marginTop: 8 },
  modalSub: { fontSize: 13, color: colors.muted, marginTop: 4, marginBottom: 16, textAlign: "center" },
  qrWrap: {
    padding: 14,
    backgroundColor: "#fff",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 14,
  },
  timerPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#EEF2F7",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    marginBottom: 10,
  },
  timerPillWarn: { backgroundColor: "#FEF2F2" },
  timerText: { fontSize: 13, fontWeight: "700", color: gov.navy },
  waitingRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 12 },
  waitingText: { fontSize: 13, color: colors.text, fontWeight: "600" },
  modalSteps: { width: "100%", marginBottom: 12 },
  modalStepRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 8 },
  stepNum: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: gov.navy,
    alignItems: "center",
    justifyContent: "center",
  },
  stepNumText: { color: "#fff", fontSize: 11, fontWeight: "800" },
  stepText: { fontSize: 13, color: colors.text },
  modalNote: { fontSize: 11, color: colors.muted, textAlign: "center", lineHeight: 16, marginBottom: 8 },
});