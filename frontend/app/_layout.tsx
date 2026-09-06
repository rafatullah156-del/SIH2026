import React from "react";
import { Stack } from "expo-router";
import { PaperProvider } from "react-native-paper";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { paperTheme, colors, gov } from "../constants/theme";

const queryClient = new QueryClient();

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <PaperProvider theme={paperTheme}>
        <Stack
          screenOptions={{
            headerShown: true,
            headerStyle: { backgroundColor: gov.navy },
            headerTintColor: "#ffffff",
            headerTitleStyle: { fontWeight: "700", color: "#ffffff" },
            contentStyle: { backgroundColor: colors.background },
          }}
        >
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="scan/new" options={{ title: "New Scan" }} />
          <Stack.Screen name="scan/processing" options={{ title: "Processing" }} />
          <Stack.Screen name="scan/[scanId]" options={{ title: "Compliance Report" }} />
          <Stack.Screen name="quick-upload" options={{ title: "Quick Upload" }} />
          <Stack.Screen name="scan/quick-upload" options={{ title: "Quick Upload" }} />
        </Stack>
      </PaperProvider>
    </QueryClientProvider>
  );
}