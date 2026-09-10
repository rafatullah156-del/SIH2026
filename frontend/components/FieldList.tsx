import React, { useMemo, useState } from "react";
import { View, Text, StyleSheet, Platform, Alert } from "react-native";
import { Card, Chip, Divider, TextInput, Button, SegmentedButtons } from "react-native-paper";
import type { ExtractedField } from "../lib/types";
import { api, errorToString } from "../lib/api";

interface FieldListProps {
  fields?: ExtractedField[];
  scanId?: string;
  violations?: any[];
}

type Role = "consumer" | "official";

const sevColor = (sev: string) => {
  const s = (sev || "").toLowerCase();
  if (s === "high") return "#ef4444";
  if (s === "medium") return "#f59e0b";
  return "#3b82f6";
};

function pickField(fields: ExtractedField[] | undefined, keys: string[]) {
  if (!Array.isArray(fields)) return "";
  const lk = keys.map((k) => k.toLowerCase());
  for (const f of fields) {
    const name = (f?.name || "").toLowerCase();
    const val = (f?.value || "").trim();
    if (!name || !val) continue;
    if (lk.some((k) => name.includes(k))) return val;
  }
  return "";
}

function buildFindingsText(violations?: any[]) {
  if (!Array.isArray(violations) || violations.length === 0) {
    return "No violations detected by system.";
  }
  return violations
    .map((v, i) => {
      const title = v?.title || v?.code || v?.type || `Violation ${i + 1}`;
      const msg = v?.message || v?.detail || v?.description || "";
      const rule = v?.rule || v?.ruleCitation || v?.ruleRef || "";
      const sev = (v?.severity || "").toUpperCase();
      return [
        `${i + 1}. ${title}${sev ? ` [${sev}]` : ""}`,
        msg ? `   - ${msg}` : "",
        rule ? `   - Rule: ${rule}` : "",
      ]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n");
}

function showAlert(title: string, message: string) {
  if (Platform.OS === "web") {
    window.alert(`${title}\n\n${message}`);
  } else {
    Alert.alert(title, message);
  }
}

export default function FieldList({ fields, scanId, violations }: FieldListProps) {
  const [role, setRole] = useState<Role>("consumer");

  // shared
  const [district, setDistrict] = useState("");
  const [state, setState] = useState("");
  const [remarks, setRemarks] = useState("");
  const [productOverride, setProductOverride] = useState("");
  const [manufacturerOverride, setManufacturerOverride] = useState("");

  // consumer-specific
  const [consumerName, setConsumerName] = useState("");
  const [consumerContact, setConsumerContact] = useState("");

  // official-specific
  const [officerName, setOfficerName] = useState("");
  const [officerDesignation, setOfficerDesignation] = useState("");
  const [officerContact, setOfficerContact] = useState("");
  const [actionTaken, setActionTaken] = useState("Notice Issued");

  const [submitting, setSubmitting] = useState(false);
  const [resultRef, setResultRef] = useState<string | null>(null);

  const autoProduct = useMemo(
    () => pickField(fields, ["product", "commodity", "item"]) || pickField(fields, ["brand"]),
    [fields]
  );
  const autoManufacturer = useMemo(
    () => pickField(fields, ["manufacturer", "packer", "marketed"]),
    [fields]
  );

  const sevCounts = useMemo(() => {
    const c = { high: 0, medium: 0, low: 0 };
    if (Array.isArray(violations)) {
      for (const v of violations) {
        const s = (v?.severity || "low").toLowerCase();
        if (s === "high") c.high++;
        else if (s === "medium") c.medium++;
        else c.low++;
      }
    }
    return c;
  }, [violations]);

  const violationSummary = useMemo(() => buildFindingsText(violations), [violations]);

  const canSubmit = useMemo(() => {
    if (!scanId) return false;
    if (role === "consumer") {
      return !!consumerName && !!consumerContact;
    }
    return !!officerName && !!officerDesignation && !!officerContact;
  }, [role, scanId, consumerName, consumerContact, officerName, officerDesignation, officerContact]);

  const handleFileComplaint = async () => {
    if (!scanId) {
      showAlert("Error", "Scan ID missing. Cannot file complaint.");
      return;
    }
    setSubmitting(true);
    setResultRef(null);
    try {
      const productName = productOverride || autoProduct || "Not specified";
      const manufacturerName = manufacturerOverride || autoManufacturer || "Not specified";

      const payload =
        role === "consumer"
          ? {
              scanId,
              productName,
              manufacturerName,
              violationSummary,
              officerName: consumerName,
              officerDesignation: "Consumer / Public Complainant",
              officerContact: consumerContact,
              district,
              state,
              actionTaken: "Complaint Filed by Consumer",
              remarks,
            }
          : {
              scanId,
              productName,
              manufacturerName,
              violationSummary,
              officerName,
              officerDesignation,
              officerContact,
              district,
              state,
              actionTaken,
              remarks,
            };

      const res = await api.fileComplaint(payload);
      setResultRef(res.complaintRef);
      showAlert("Complaint Filed ✅", `Reference: ${res.complaintRef}\n\n${res.message}`);
    } catch (e: any) {
      showAlert("Failed to file complaint", errorToString(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.title}>File a Complaint</Text>

        <View style={styles.chips}>
          <Chip style={[styles.chip, { backgroundColor: sevColor("high") }]} textStyle={styles.chipText}>
            High: {sevCounts.high}
          </Chip>
          <Chip style={[styles.chip, { backgroundColor: sevColor("medium") }]} textStyle={styles.chipText}>
            Medium: {sevCounts.medium}
          </Chip>
          <Chip style={[styles.chip, { backgroundColor: sevColor("low") }]} textStyle={styles.chipText}>
            Low: {sevCounts.low}
          </Chip>
        </View>

        <Divider style={{ marginVertical: 12 }} />

        <Text style={styles.roleLabel}>Filing as:</Text>
        <SegmentedButtons
          value={role}
          onValueChange={(v) => setRole(v as Role)}
          buttons={[
            { value: "consumer", label: "Consumer" },
            { value: "official", label: "Government Official" },
          ]}
          style={{ marginTop: 6, marginBottom: 12 }}
        />

        <View style={styles.row}>
          <TextInput
            style={styles.half}
            label="Product Name"
            value={productOverride}
            onChangeText={setProductOverride}
            placeholder={autoProduct ? `Auto: ${autoProduct}` : "Enter product name"}
          />
          <TextInput
            style={styles.half}
            label="Manufacturer"
            value={manufacturerOverride}
            onChangeText={setManufacturerOverride}
            placeholder={autoManufacturer ? `Auto: ${autoManufacturer}` : "Enter manufacturer"}
          />
        </View>

        {role === "consumer" ? (
          <View style={styles.row}>
            <TextInput style={styles.half} label="Your Name *" value={consumerName} onChangeText={setConsumerName} />
            <TextInput
              style={styles.half}
              label="Your Contact *"
              value={consumerContact}
              onChangeText={setConsumerContact}
            />
          </View>
        ) : (
          <>
            <View style={styles.row}>
              <TextInput
                style={styles.half}
                label="Officer Name *"
                value={officerName}
                onChangeText={setOfficerName}
              />
              <TextInput
                style={styles.half}
                label="Designation *"
                value={officerDesignation}
                onChangeText={setOfficerDesignation}
              />
            </View>
            <View style={styles.row}>
              <TextInput
                style={styles.half}
                label="Officer Contact *"
                value={officerContact}
                onChangeText={setOfficerContact}
              />
              <TextInput style={styles.half} label="Action Taken" value={actionTaken} onChangeText={setActionTaken} />
            </View>
          </>
        )}

        <View style={styles.row}>
          <TextInput style={styles.half} label="District" value={district} onChangeText={setDistrict} />
          <TextInput style={styles.half} label="State" value={state} onChangeText={setState} />
        </View>

        <TextInput
          label="Remarks (optional)"
          value={remarks}
          onChangeText={setRemarks}
          multiline
          numberOfLines={2}
          style={{ marginTop: 10 }}
        />

        <Divider style={{ marginVertical: 12 }} />

        <Text style={styles.previewLabel}>Violation Summary (auto-generated)</Text>
        <TextInput value={violationSummary} multiline numberOfLines={6} editable={false} style={{ marginTop: 6 }} />

        <View style={styles.btnRow}>
          <Button mode="contained" icon="send" loading={submitting} disabled={!canSubmit || submitting} onPress={handleFileComplaint}>
            File Complaint
          </Button>
        </View>

        {resultRef ? (
          <View style={styles.successBox}>
            <Text style={styles.successText}>✅ Filed successfully. Reference: {resultRef}</Text>
          </View>
        ) : null}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: 16 },
  title: { fontSize: 18, fontWeight: "700" },

  chips: { flexDirection: "row", gap: 8, marginTop: 10, flexWrap: "wrap" },
  chip: { height: 28 },
  chipText: { color: "#fff", fontSize: 12 },

  roleLabel: { fontSize: 13, fontWeight: "600", color: "#666" },

  row: { flexDirection: "row", gap: 10, marginTop: 8 },
  half: { flex: 1 },

  previewLabel: { fontSize: 12, fontWeight: "700", color: "#666" },

  btnRow: { flexDirection: "row", gap: 10, marginTop: 14, justifyContent: "flex-end" },

  successBox: {
    marginTop: 12,
    padding: 10,
    borderRadius: 8,
    backgroundColor: "#dcfce7",
    borderColor: "#22c55e",
    borderWidth: 1,
  },
  successText: { color: "#166534", fontWeight: "600" },
});