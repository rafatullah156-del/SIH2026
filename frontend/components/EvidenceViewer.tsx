import React, { useState, useEffect } from "react";
import { View, Image, StyleSheet, Dimensions, ActivityIndicator, Text } from "react-native";
import type { BBox } from "../lib/types";

interface EvidenceViewerProps {
  imageUrl: string;
  originalWidth?: number;
  originalHeight?: number;
  bbox?: BBox;
  highlightColor?: string;
  maxHeight?: number;
}

export default function EvidenceViewer({
  imageUrl,
  originalWidth,
  originalHeight,
  bbox,
  highlightColor = "#ef4444",
  maxHeight = 400,
}: EvidenceViewerProps) {
  const [displaySize, setDisplaySize] = useState<{ width: number; height: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const screenWidth = Dimensions.get("window").width;

  const computeDisplaySize = (imgW: number, imgH: number) => {
    const containerWidth = Math.min(screenWidth - 64, 600);
    const scale = containerWidth / imgW;
    let displayHeight = imgH * scale;
    let displayWidth = containerWidth;
    if (displayHeight > maxHeight) {
      displayHeight = maxHeight;
      displayWidth = maxHeight * (imgW / imgH);
    }
    setDisplaySize({ width: displayWidth, height: displayHeight });
  };

  useEffect(() => {
    if (originalWidth && originalHeight) {
      computeDisplaySize(originalWidth, originalHeight);
    } else {
      Image.getSize(
        imageUrl,
        (w, h) => computeDisplaySize(w, h),
        () => setError(true)
      );
    }
  }, [imageUrl, originalWidth, originalHeight]);

  if (error) {
    return (
      <View style={styles.errorBox}>
        <Text style={styles.errorText}>Failed to load image</Text>
      </View>
    );
  }

  const containerWidth = displaySize?.width || Math.min(screenWidth - 64, 600);
  const containerHeight = displaySize?.height || maxHeight;

  const scaleX = originalWidth ? containerWidth / originalWidth : 1;
  const scaleY = originalHeight ? containerHeight / originalHeight : 1;

  return (
    <View style={[styles.container, { width: containerWidth, height: containerHeight }]}>
      {loading && <ActivityIndicator style={StyleSheet.absoluteFill} size="large" />}
      <Image
        source={{ uri: imageUrl }}
        style={{ width: containerWidth, height: containerHeight }}
        resizeMode="contain"
        onLoad={() => setLoading(false)}
        onError={() => {
          setError(true);
          setLoading(false);
        }}
      />
      {bbox && originalWidth && originalHeight && (
        <View
          pointerEvents="none"
          style={[
            styles.bboxOverlay,
            {
              left: bbox.x * scaleX,
              top: bbox.y * scaleY,
              width: bbox.w * scaleX,
              height: bbox.h * scaleY,
              borderColor: highlightColor,
            },
          ]}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "relative",
    backgroundColor: "#f3f4f6",
    borderRadius: 8,
    overflow: "hidden",
    alignSelf: "center",
  },
  bboxOverlay: {
    position: "absolute",
    borderWidth: 3,
    borderRadius: 2,
    backgroundColor: "rgba(239, 68, 68, 0.15)",
  },
  errorBox: { padding: 40, alignItems: "center", backgroundColor: "#fef2f2", borderRadius: 8 },
  errorText: { color: "#dc2626" },
});