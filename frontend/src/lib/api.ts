import type {
  Analytics,
  AttendanceRecord,
  AttendanceSummary,
  Dashboard,
  Health,
  LiveStatus,
  ModelsStatus,
  ProcessingStatus,
  RecommendationResponse,
  Report,
  RosterEntry,
  Session,
  SessionDetail,
  Settings,
  UploadResult,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";

export class ApiError extends Error {
  status: number;
  code: string;
  detail?: unknown;

  constructor(status: number, code: string, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Could not reach the local ClassMind backend. Is it running on port 8000?",
    );
  }

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let code = "http_error";
    let detail: unknown;
    if (contentType.includes("application/json")) {
      try {
        const body = (await response.json()) as {
          error?: { code?: string; message?: string; detail?: unknown };
        };
        code = body.error?.code ?? code;
        message = body.error?.message ?? message;
        detail = body.error?.detail;
      } catch {
        // keep the generic message
      }
    }
    throw new ApiError(response.status, code, message, detail);
  }

  if (contentType.includes("application/json")) return (await response.json()) as T;
  return (await response.text()) as unknown as T;
}

export const api = {
  base: BASE,

  health: () => request<Health>("/health"),
  dashboard: () => request<Dashboard>("/dashboard"),

  listSessions: (params?: { status?: string; q?: string; includeDemo?: boolean }) => {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.q) search.set("q", params.q);
    if (params?.includeDemo === false) search.set("include_demo", "false");
    const query = search.toString();
    return request<Session[]>(`/sessions${query ? `?${query}` : ""}`);
  },
  getSession: (id: string) => request<SessionDetail>(`/sessions/${id}`),
  createSession: (payload: Record<string, unknown>) =>
    request<Session>("/sessions", { method: "POST", body: JSON.stringify(payload) }),
  deleteSession: (id: string) => request<void>(`/sessions/${id}`, { method: "DELETE" }),

  uploadMedia: (id: string, video: File | null, audio: File | null) => {
    const form = new FormData();
    if (video) form.append("video", video);
    if (audio) form.append("audio", audio);
    return request<UploadResult>(`/sessions/${id}/upload`, { method: "POST", body: form });
  },
  processSession: (id: string) =>
    request<{ session_id: string; status: string; job_id: string; message: string }>(
      `/sessions/${id}/process`,
      { method: "POST" },
    ),
  getStatus: (id: string) => request<ProcessingStatus>(`/sessions/${id}/status`),

  startLive: (id: string, payload: { camera_index?: number; max_seconds?: number }) =>
    request<LiveStatus>(`/sessions/${id}/live/start`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  stopLive: (id: string) =>
    request<LiveStatus>(`/sessions/${id}/live/stop`, { method: "POST" }),
  liveStatus: (id: string) => request<LiveStatus>(`/sessions/${id}/live/status`),

  attendance: (id: string) => request<AttendanceSummary>(`/sessions/${id}/attendance`),
  analytics: (id: string) => request<Analytics>(`/sessions/${id}/analytics`),
  recommendations: (id: string) =>
    request<RecommendationResponse>(`/sessions/${id}/recommendations`),
  report: (id: string) => request<Report>(`/sessions/${id}/report`),

  roster: () => request<RosterEntry[]>("/roster"),
  createRoster: (payload: { name: string; external_id?: string | null; class_label?: string | null }) =>
    request<RosterEntry>("/roster", { method: "POST", body: JSON.stringify(payload) }),
  deleteRoster: (id: string) => request<void>(`/roster/${id}`, { method: "DELETE" }),
  mapTrack: (sessionId: string, trackId: string, rosterId: string | null, confirmManual = true) =>
    request<AttendanceRecord>(`/sessions/${sessionId}/attendance/${trackId}/map`, {
      method: "POST",
      body: JSON.stringify({ roster_id: rosterId, confirm_manual: confirmManual }),
    }),

  settings: () => request<Settings>("/settings"),
  updateSettings: (payload: Record<string, unknown>) =>
    request<Settings>("/settings", { method: "PUT", body: JSON.stringify(payload) }),
  models: () => request<ModelsStatus>("/settings/models"),
  applyRetention: () =>
    request<{ removed_sessions: number }>("/settings/retention/apply", { method: "POST" }),

  seedDemo: () => request<Session>("/demo/seed", { method: "POST" }),
  clearDemo: () =>
    request<{ removed_sessions: number; message: string }>("/demo", { method: "DELETE" }),

  reportUrl: (id: string, kind: "html" | "csv" = "html") =>
    `${BASE}/sessions/${id}/report.${kind}`,
  attendanceCsvUrl: (id: string) => `${BASE}/sessions/${id}/attendance.csv`,
  reportDownloadUrl: (id: string) => `${BASE}/sessions/${id}/report.html?download=true`,
};
