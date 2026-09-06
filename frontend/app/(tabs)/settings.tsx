import React from "react";
import { StyleSheet, ScrollView, Text } from "react-native";
import { List, Divider } from "react-native-paper";
import { API_URL } from "../../lib/api";

export default function SettingsScreen() {
  return (
    <ScrollView style={styles.container}>
      <Text style={styles.heading}>Settings</Text>
      <List.Section>
        <List.Subheader>Connection</List.Subheader>
        <List.Item title="Backend API URL" description={API_URL} left={(props) => <List.Icon {...props} icon="server" />} />
        <Divider />
        <List.Subheader>App Info</List.Subheader>
        <List.Item title="Version" description="1.0.0" left={(props) => <List.Icon {...props} icon="information" />} />
        <List.Item
          title="SIH Problem Statement"
          description="SIH26034 - Legal Metrology Compliance Checker"
          left={(props) => <List.Icon {...props} icon="file-document" />}
        />
      </List.Section>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  heading: { fontSize: 22, fontWeight: "700", padding: 16, paddingBottom: 0 },
});