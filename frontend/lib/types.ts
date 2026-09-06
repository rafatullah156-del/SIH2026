export type PanelType = "front" | "back" | "side" | "calibration";

export type ScanStatus =
  | "created"
  | "uploading"
  | "queued"
  | "processing"
  | "done"
  | "failed";

export type Severity = "high" | "medium" | "low";

// All possible violation codes per LMPC 2011
export type ViolationCode =
  // Rule 6 - Mandatory declarations
  | "COMMON_NAME_MISSING"
  | "MRP_MISSING"
  | "NET_QTY_MISSING"
  | "MFD_MISSING"
  | "MANUFACTURER_MISSING"
  | "CONSUMER_CARE_MISSING"
  // Rule 6 specific
  | "MRP_TAX_INCLUSIVE_MISSING"
  | "DUAL_MRP_PROHIBITED"
  | "MFD_DATE_FORMAT_WRONG"
  | "MANUFACTURER_ADDRESS_INCOMPLETE"
  | "COUNTRY_OF_ORIGIN_MISSING"
  | "BEST_BEFORE_MISSING"
  // Rule 7 - Placement
  | "COMMON_NAME_PLACEMENT"
  | "MRP_PLACEMENT"
  | "NET_QTY_PLACEMENT"
  // Rule 8 - Font size
  | "NET_QTY_NUMERAL_HEIGHT"
  | "NET_QTY_NUMERAL_HEIGHT_REVIEW"
  | "FONT_SIZE_NOT_CHECKED_REVIEW"
  // Rule 9 - Readability
  | "NO_TEXT_DETECTED_REVIEW"
  | "LOW_READABILITY"
  | "LOW_OCR_CONFIDENCE_REVIEW"
  // Rule 18 - E-commerce
  | "ECOMMERCE_DECLARATION_INCOMPLETE"
  // FSSAI
  | "FSSAI_LICENSE_MISSING_REVIEW"
  | "FSSAI_LICENSE_FORMAT_INVALID"
  // Standard pack
  | "NON_STANDARD_PACK_SIZE_REVIEW"
  // Review variants
  | `${string}_REVIEW`;

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

// All possible extracted field names
export type FieldName =
  | "common_name"
  | "mrp"
  | "net_quantity"
  | "mfd_date"
  | "manufacturer"
  | "consumer_care"
  | "best_before"
  | "country_of_origin"
  | "importer"
  | "fssai_license"
  | "batch_no"
  | "barcode"
  | "food_category_detected"
  | "ecommerce_indicator";

export interface FieldMeta {
  // MRP specific
  amount?: number;
  label_found?: boolean;
  tax_text_found?: boolean;
  dual_mrp_detected?: boolean;
  unit_price?: { amount: number; per: string } | null;
  // Net quantity specific
  value?: number;
  unit?: string;
  base_g_or_ml?: number;
  standard_pack?: boolean | null;
  // Date specific
  format_valid?: boolean;
  unlabelled_date?: boolean;
  // Manufacturer specific
  pin_found?: boolean;
  entity_found?: boolean;
  address_complete?: boolean;
  // Consumer care specific
  phones?: string[];
  emails?: string[];
  // Country of origin
  is_import?: boolean;
  conditional_mandatory?: boolean;
  // General
  optional?: boolean;
  note?: string;
  inferred_from?: string;
}

export interface ExtractedField {
  name: FieldName | string;
  value: string | null;
  confidence: number;
  panelType: PanelType;
  imageId: string;
  bbox: BBox | null;
  meta?: FieldMeta;
}

export interface Violation {
  code: ViolationCode | string;
  severity: Severity;
  field: FieldName | string | null;
  message: string;
  panelType: PanelType | null;
  imageId: string | null;
  bbox: BBox | null;
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
  violationCount?: number;
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
  scansByStatus?: Record<ScanStatus, number>;
  violationsByType?: Record<string, number>;
  violationsBySeverity?: Record<Severity, number>;
  recentScans?: ScanListItem[];
}

export interface UploadFile {
  uri: string;
  fileName?: string;
  mimeType?: string;
}

// Score interpretation
export function scoreLabel(score: number): {
  label: string;
  color: string;
  emoji: string;
} {
  if (score >= 90) return { label: "Compliant", color: "#16a34a", emoji: "✅" };
  if (score >= 70) return { label: "Minor Issues", color: "#d97706", emoji: "⚠️" };
  if (score >= 50) return { label: "Major Violations", color: "#ea580c", emoji: "🔴" };
  return { label: "Non-Compliant", color: "#dc2626", emoji: "❌" };
}

// Human-readable rule references
export const RULE_DESCRIPTIONS: Record<string, string> = {
  COMMON_NAME_MISSING: "Rule 6(1)(b) — Common name of commodity missing",
  MRP_MISSING: "Rule 6(1)(e) — MRP not declared",
  NET_QTY_MISSING: "Rule 6(1)(c) — Net quantity not declared",
  MFD_MISSING: "Rule 6(1)(d) — Month & year of manufacture missing",
  MANUFACTURER_MISSING: "Rule 6(1)(a) — Manufacturer details missing",
  CONSUMER_CARE_MISSING: "Rule 6(1)(f) — Consumer care contact missing",
  MRP_TAX_INCLUSIVE_MISSING: "Rule 2(m) — 'Inclusive of all taxes' wording absent",
  DUAL_MRP_PROHIBITED: "Rule 6(1)(e) — Dual MRP strictly prohibited",
  MFD_DATE_FORMAT_WRONG: "Rule 6(1)(d) — Date format must be Month-Year only",
  MANUFACTURER_ADDRESS_INCOMPLETE: "Rule 6(1)(a) — Address incomplete (no PIN)",
  COUNTRY_OF_ORIGIN_MISSING: "Rule 6(1)(a) — Country of origin missing for imported goods",
  BEST_BEFORE_MISSING: "Rule 6(2) — Best before/expiry mandatory for food",
  ECOMMERCE_DECLARATION_INCOMPLETE: "Rule 18 — E-commerce declarations incomplete",
  NON_STANDARD_PACK_SIZE_REVIEW: "Schedule II — Non-standard pack size",
  NET_QTY_NUMERAL_HEIGHT: "Rule 8 — Net quantity numerals too small",
  FSSAI_LICENSE_MISSING_REVIEW: "FSS Act — FSSAI license not found",
  FSSAI_LICENSE_FORMAT_INVALID: "FSS Act — FSSAI license must be 14 digits",
};