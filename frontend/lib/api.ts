import axios, { AxiosInstance } from "axios";
import { Platform } from "react-native";
import type {
  ScanResult,
  ScanListItem,
  PairTokenResponse,
  DashboardSummary,
  PanelType,
  UploadFile,
} from "./types";

export const API_URL = (process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export const httpClient: AxiosInstance = axios.create({ baseURL: API_URL, timeout: 30000 });

// ---------- Errors ----------

export class HttpError extends Error {
  response: { status: number; data: any };
  constructor(status: number, data: any) {
    super(typeof data?.detail === "string" ? data.detail : `HTTP ${status}`);
    this.response = { status, data };
  }
}

/** Always returns a plain string safe to render in <Text> (handles FastAPI 422 arrays). */
export function errorToString(e: any): string {
  const detail = e?.response?.data?.detail ?? e?.response?.data ?? e?.message;
  if (!detail) return "Something went wrong";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d?.msg === "string" ? d.msg : JSON.stringify(d))).join("\n");
  }
  if (typeof detail === "object") {
    if (typeof detail.msg === "string") return detail.msg;
    return JSON.stringify(detail);
  }
  return String(detail);
}

// ---------- Helpers ----------

function toAbsoluteUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

function normalizeScan(raw: any): ScanResult {
  return {
    ...raw,
    images: (raw.images || []).map((im: any) => ({ ...im, viewUrl: toAbsoluteUrl(im.viewUrl) || im.viewUrl })),
    report: raw.report
      ? {
          pdfUrl: toAbsoluteUrl(raw.report.pdfUrl),
          jsonUrl: toAbsoluteUrl(raw.report.jsonUrl),
          csvUrl: toAbsoluteUrl(raw.report.csvUrl),
        }
      : undefined,
  };
}

/** Web: convert uri (blob:/data:) → real File. Native: RN file descriptor. */
async function toFilePart(file: UploadFile, fallbackName: string, fallbackType: string): Promise<any> {
  const name = file.fileName || fallbackName;
  const type = file.mimeType || fallbackType;
  if (Platform.OS === "web") {
    const blob = await (await fetch(file.uri)).blob();
    return new File([blob], name, { type: blob.type || type });
  }
  return { uri: file.uri, name, type };
}

async function parseBody(res: Response) {
  const ct = res.headers.get("content-type") || "";
  try {
    return ct.includes("application/json") ? await res.json() : await res.text();
  } catch {
    return null;
  }
}

/** Multipart via fetch (lets browser/RN set the boundary correctly). */
async function postMultipart<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { method: "POST", body: form });
  const body = await parseBody(res);
  if (!res.ok) throw new HttpError(res.status, body);
  return body as T;
}

// ---------- API ----------

export const api = {
  async createScan(): Promise<string> {
    const { data } = await httpClient.post<{ scanId: string }>("/scans");
    return data.scanId;
  },

  async uploadScanImage(scanId: string, panelType: PanelType, file: UploadFile): Promise<string> {
    const form = new FormData();
    form.append("panelType", panelType);
    form.append("file", await toFilePart(file, `${panelType}.jpg`, "image/jpeg"));
    const data = await postMultipart<{ imageId: string }>(`/scans/${scanId}/images`, form);
    return data.imageId;
  },

  async submitScan(scanId: string): Promise<{ ok: boolean; status: string }> {
    const { data } = await httpClient.post(`/scans/${scanId}/submit`);
    return data;
  },

  async getScan(scanId: string): Promise<ScanResult> {
    const { data } = await httpClient.get(`/scans/${scanId}`);
    return normalizeScan(data);
  },

  getReportPdfUrl(scanId: string): string {
    return `${API_URL}/scans/${scanId}/report.pdf`;
  },

  getReportJsonUrl(scanId: string): string {
    return `${API_URL}/scans/${scanId}/report.json`;
  },

  async listScans(params?: { page?: number; pageSize?: number }): Promise<ScanListItem[]> {
    const { data } = await httpClient.get("/scans", { params });
    return Array.isArray(data) ? data : data.items || [];
  },

  async getDashboardSummary(params?: { from?: string; to?: string }): Promise<DashboardSummary> {
    const { data } = await httpClient.get("/dashboard/summary", { params });
    return data;
  },

  async createPairToken(scanId: string): Promise<PairTokenResponse> {
    const { data } = await httpClient.post(`/scans/${scanId}/pair-token`);
    return data;
  },

  async pairSubmit(
    token: string,
    files: { front: UploadFile; back: UploadFile; calibration?: UploadFile }
  ): Promise<{ ok: boolean; scanId: string; status: string }> {
    const form = new FormData();
    form.append("front", await toFilePart(files.front, "front.jpg", "image/jpeg"));
    form.append("back", await toFilePart(files.back, "back.jpg", "image/jpeg"));
    if (files.calibration) {
      form.append("calibration", await toFilePart(files.calibration, "calibration.jpg", "image/jpeg"));
    }
    return postMultipart(`/pair/${token}/submit`, form);
  },
};