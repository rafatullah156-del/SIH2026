export type PanelType = "front" | "back" | "side" | "calibration";

export type ScanStatus =
  | "created"
  | "uploading"
  | "queued"
  | "processing"
  | "done"
  | "failed";

export type Severity = "high" | "medium" | "low";

export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ScanImage {
  imageId: string;
  panelType: PanelType;
  viewUrl: string;
  width?: number;
  height?: number;
}

export interface ExtractedField {
  name: string;
  value: string;
  confidence: number;
  panelType: PanelType;
  imageId: string;
  bbox: BBox;
}

export interface Violation {
  code: string;
  severity: Severity;
  field: string;
  message: string;
  panelType: PanelType;
  imageId: string;
  bbox: BBox;
}

export interface ReportInfo {
  pdfUrl?: string;
  jsonUrl?: string;
  csvUrl?: string;
}

export interface ScanResult {
  scanId: string;
  status: ScanStatus;
  score?: number;
  images: ScanImage[];
  fields: ExtractedField[];
  violations: Violation[];
  report?: ReportInfo;
  createdAt: string;
  updatedAt: string;
  error?: string;
}

export interface ScanListItem {
  scanId: string;
  status: ScanStatus;
  score?: number;
  createdAt: string;
}

export interface PairTokenResponse {
  token: string;
  joinUrl: string;
  expiresAt: string;
}

export interface DashboardSummary {
  totalScans: number;
  totalViolations: number;
  averageScore: number;
  violationsByType?: Record<string, number>;
}

export interface UploadFile {
  uri: string;
  fileName?: string;
  mimeType?: string;
}