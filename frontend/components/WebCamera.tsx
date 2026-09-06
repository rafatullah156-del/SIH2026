import React, { useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet, Platform } from "react-native";
import { Button, Modal, Portal } from "react-native-paper";
import { colors } from "../constants/theme";

interface WebCameraProps {
  visible: boolean;
  onClose: () => void;
  onCapture: (dataUrl: string) => void;
}

export default function WebCamera({ visible, onClose, onCapture }: WebCameraProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [facing, setFacing] = useState<"environment" | "user">("environment");
  const [ready, setReady] = useState(false);

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  };

  useEffect(() => {
    if (Platform.OS !== "web" || !visible) return;
    let cancelled = false;
    setError(null);
    setReady(false);

    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: facing, width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          setReady(true);
        }
      } catch (e: any) {
        setError(e?.message || "Camera not available on this device/browser.");
      }
    })();

    return () => {
      cancelled = true;
      stopStream();
    };
  }, [visible, facing]);

  const capture = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
    stopStream();
    onCapture(dataUrl);
    onClose();
  };

  const handleClose = () => {
    stopStream();
    onClose();
  };

  if (Platform.OS !== "web") return null;

  return (
    <Portal>
      <Modal visible={visible} onDismiss={handleClose} contentContainerStyle={styles.modal}>
        <Text style={styles.title}>Take Photo</Text>

        {error ? (
          <Text style={styles.error}>{error}</Text>
        ) : (
          <View style={styles.videoWrap}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{ width: "100%", maxHeight: 420, borderRadius: 8, background: "#000" }}
            />
          </View>
        )}

        <View style={styles.row}>
          <Button mode="outlined" onPress={handleClose} textColor={colors.text}>
            Cancel
          </Button>
          {!error && (
            <>
              <Button
                mode="outlined"
                icon="camera-flip"
                onPress={() => setFacing((f) => (f === "environment" ? "user" : "environment"))}
                textColor={colors.text}
              >
                Flip
              </Button>
              <Button mode="contained" icon="camera" onPress={capture} disabled={!ready}>
                Capture
              </Button>
            </>
          )}
        </View>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  modal: {
    backgroundColor: colors.surface,
    margin: 20,
    borderRadius: 12,
    padding: 16,
    maxWidth: 720,
    width: "90%",
    alignSelf: "center",
  },
  title: { fontSize: 18, fontWeight: "700", color: colors.text, marginBottom: 12 },
  videoWrap: { width: "100%", alignItems: "center", marginBottom: 12 },
  error: { color: colors.danger, marginBottom: 12 },
  row: { flexDirection: "row", justifyContent: "flex-end", gap: 10, flexWrap: "wrap" },
});