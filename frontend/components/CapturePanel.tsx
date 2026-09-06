import React, { useState } from "react";
import { View, Text, Image, StyleSheet, Platform, Alert } from "react-native";
import { Button, Card } from "react-native-paper";
import * as ImagePicker from "expo-image-picker";
import WebCamera from "./WebCamera";
import { useBreakpoint } from "../lib/breakpoints";
import { colors } from "../constants/theme";
import type { UploadFile } from "../lib/types";

interface CapturePanelProps {
  label: string;
  required?: boolean;
  file: UploadFile | null;
  onChange: (file: UploadFile | null) => void;
}

const isWeb = Platform.OS === "web";

function notify(msg: string) {
  if (isWeb) window.alert(msg);
  else Alert.alert("Camera", msg);
}

export default function CapturePanel({ label, required = false, file, onChange }: CapturePanelProps) {
  const [loading, setLoading] = useState(false);
  const [webcamOpen, setWebcamOpen] = useState(false);
  const { isDesktop } = useBreakpoint();

  const slug = label.toLowerCase().replace(/[^a-z0-9]+/g, "-");

  // Laptop browser with webcam API available (needs https or localhost)
  const hasWebcamApi =
    isWeb && typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

  const setFromAsset = (asset: ImagePicker.ImagePickerAsset) => {
    onChange({
      uri: asset.uri,
      fileName: asset.fileName || `${slug}.jpg`,
      mimeType: asset.mimeType || "image/jpeg",
    });
  };

  const openCamera = async () => {
    // Laptop/desktop browser → live webcam modal
    if (isWeb && isDesktop && hasWebcamApi) {
      setWebcamOpen(true);
      return;
    }
    // Native app OR mobile browser → device camera
    setLoading(true);
    try {
      if (!isWeb) {
        const perm = await ImagePicker.requestCameraPermissionsAsync();
        if (!perm.granted) {
          notify("Camera permission is required.");
          return;
        }
      }
      const result = await ImagePicker.launchCameraAsync({ quality: 0.85 });
      if (!result.canceled && result.assets?.[0]) setFromAsset(result.assets[0]);
    } catch (e: any) {
      notify(e?.message || "Could not open camera.");
    } finally {
      setLoading(false);
    }
  };

  const openLibrary = async () => {
    setLoading(true);
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        quality: 0.85,
      });
      if (!result.canceled && result.assets?.[0]) setFromAsset(result.assets[0]);
    } catch (e: any) {
      notify(e?.message || "Could not open files.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card style={styles.card} mode="outlined">
      <Card.Content>
        <Text style={styles.label}>
          {label} {required ? <Text style={styles.required}>*</Text> : null}
        </Text>

        {file ? (
          <View style={styles.previewWrap}>
            <Image source={{ uri: file.uri }} style={styles.preview} resizeMode="cover" />
            <View style={styles.actionsRow}>
              <Button mode="outlined" icon="camera-retake" onPress={openCamera} textColor={colors.text} style={styles.btn}>
                Retake
              </Button>
              <Button mode="text" icon="close" onPress={() => onChange(null)} textColor={colors.danger} style={styles.btn}>
                Remove
              </Button>
            </View>
          </View>
        ) : (
          <View style={styles.actionsRow}>
            <Button mode="contained" icon="camera" onPress={openCamera} loading={loading} style={styles.btn}>
              Take Photo
            </Button>
            <Button mode="outlined" icon="image" onPress={openLibrary} loading={loading} textColor={colors.text} style={styles.btn}>
              {isWeb ? "Upload File" : "Gallery"}
            </Button>
          </View>
        )}
      </Card.Content>

      <WebCamera
        visible={webcamOpen}
        onClose={() => setWebcamOpen(false)}
        onCapture={(dataUrl) => onChange({ uri: dataUrl, fileName: `${slug}.jpg`, mimeType: "image/jpeg" })}
      />
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: 16, backgroundColor: colors.surface, borderColor: colors.border },
  label: { fontSize: 16, fontWeight: "700", color: colors.text, marginBottom: 12 },
  required: { color: colors.danger },
  actionsRow: { flexDirection: "row", gap: 12, flexWrap: "wrap" },
  btn: { flex: 1, minWidth: 130 },
  previewWrap: { width: "100%" },
  preview: { width: "100%", height: 220, borderRadius: 8, marginBottom: 12, backgroundColor: "#e5e7eb" },
});