import React from "react";
import { Tabs } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import GovHeader from "../../components/GovHeader";
import { gov } from "../../constants/theme";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        header: () => <GovHeader />,
        tabBarActiveTintColor: gov.navy,
        tabBarInactiveTintColor: "#64748b",
        tabBarStyle: { borderTopColor: "#e2e8f0", backgroundColor: "#ffffff" },
        tabBarLabelStyle: { fontWeight: "600" },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: "Home", tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name="home" color={color} size={size} /> }}
      />
      <Tabs.Screen
        name="history"
        options={{ title: "History", tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name="history" color={color} size={size} /> }}
      />
      <Tabs.Screen
        name="settings"
        options={{ title: "Settings", tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name="cog" color={color} size={size} /> }}
      />
    </Tabs>
  );
}