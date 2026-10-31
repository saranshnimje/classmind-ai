export const DEFAULT_VIDEO_EXTENSIONS = [
  ".mp4",
  ".m4v",
  ".mov",
  ".avi",
  ".mkv",
  ".webm",
  ".mpeg",
  ".mpg",
];

export const DEFAULT_AUDIO_EXTENSIONS = [
  ".wav",
  ".mp3",
  ".m4a",
  ".aac",
  ".flac",
  ".ogg",
  ".opus",
];

export function fmtDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return "—";
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function fmtClock(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** For values on a 0-1 scale (ratios). */
export function fmtRatio(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

/** For values already expressed as a percentage (0-100), e.g. attendance rate. */
export function fmtRate(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(digits)}%`;
}

export function fmtScore(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso.length <= 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  if (Number.isNaN(diff)) return iso;
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return fmtDate(iso);
}

export function fmtFileSize(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    created: "Created",
    uploaded: "Media ready",
    queued: "Queued",
    processing: "Processing",
    completed: "Completed",
    failed: "Failed",
    ok: "Operational",
    degraded: "Degraded",
  };
  return labels[status] ?? status;
}

export function engagementTone(score: number | null | undefined): "high" | "medium" | "low" | "unknown" {
  if (score === null || score === undefined) return "unknown";
  if (score >= 0.6) return "high";
  if (score >= 0.35) return "medium";
  return "low";
}

export function validateMediaFile(
  file: File,
  kind: "video" | "audio",
  limits: { max_upload_mb: number; video_extensions: string[]; audio_extensions: string[] },
): string | null {
  const allowed = kind === "video" ? limits.video_extensions : limits.audio_extensions;
  const extension = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
  if (!allowed.includes(extension)) {
    return `Unsupported ${kind} format "${extension}". Allowed: ${allowed.join(", ")}`;
  }
  const maxBytes = limits.max_upload_mb * 1024 * 1024;
  if (file.size > maxBytes) {
    return `File is ${fmtFileSize(file.size)}; the limit is ${limits.max_upload_mb} MB.`;
  }
  if (file.size === 0) return "The selected file is empty.";
  return null;
}

export function toChartWindows<T extends { start_sec: number; end_sec: number }>(windows: T[]) {
  return windows.map((window, index) => ({
    ...window,
    label: fmtClock(window.start_sec),
    name: `Window ${index + 1}`,
  }));
}
