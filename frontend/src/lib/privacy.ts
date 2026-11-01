export type DeploymentMode = "hosted" | "local" | "unknown";

export function getDeploymentMode(): DeploymentMode {
  const raw = (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE;
  const mode = typeof raw === "string" ? raw.trim().toLowerCase() : "";
  if (mode === "hosted") return "hosted";
  if (mode === "local") return "local";
  return "unknown";
}

export function privacySummary() {
  const mode = getDeploymentMode();
  if (mode === "hosted") {
    return {
      title: "Hosted privacy",
      processing: "Recordings are transmitted over HTTPS to the Render backend for processing. Processing and temporary/persistent storage depend on Render's filesystem and database configuration.",
      storage: "Data location: Render (instance filesystem). Use synthetic/demo recordings unless authorization and consent are in place.",
      dataLocal: false,
    };
  }
  if (mode === "local") {
    return {
      title: "Local privacy",
      processing: "Processing occurs through the local Docker backend on this machine. Media and database use the configured local data directory/volume.",
      storage: "Data is stored according to the local Docker configuration.",
      dataLocal: true,
    };
  }
  return {
    title: "Unknown deployment mode",
    processing: "Processing location is not confirmed. Use synthetic/demo recordings unless authorization and consent are in place.",
    storage: "Data location: unconfirmed.",
    dataLocal: false,
  };
}

export function privacyPrinciples(mode: DeploymentMode): string[] {
  const common = [
    "Detected people are anonymous participant tracks until you manually map them to a roster entry.",
    "No face recognition, biometric templates, speaker identification, or emotion detection is performed.",
    "Engagement proxies are descriptive blends of observable signals, not validated assessments of attention or learning.",
    "Missing audio or video is reported as unavailable, never as low engagement.",
    "Synthetic/demo recordings should be used unless authorization and consent are in place.",
  ];
  if (mode === "hosted") {
    return [
      ...common,
      "Recordings are sent over HTTPS to the Render backend for processing.",
      "Render Free filesystem may be ephemeral; do not assume permanent persistence.",
      "No cloud AI services are used for inference or recommendations.",
    ];
  }
  if (mode === "local") {
    return [
      ...common,
      "Media stays on this machine. No media is sent to Render or any external service.",
      "No cloud uploads, no student surveillance profiles, no external AI calls.",
    ];
  }
  return [
    ...common,
    "Deployment mode unknown — do not assume local-only processing or hosted processing.",
  ];
}

export function privacyNoticeText(): string {
  const mode = getDeploymentMode();
  if (mode === "hosted") {
    return "Hosted privacy. Frontend is hosted on Vercel. Recordings are sent over HTTPS to the Render backend for processing. Processing and storage depend on Render's filesystem and database configuration. No face recognition, no biometric identification. Data location: Render (instance filesystem).";
  }
  if (mode === "local") {
    return "Local privacy. Media stays on this machine. No face recognition, no cloud uploads, no student surveillance profiles. Data is stored according to the local Docker configuration. No face recognition, no biometric identification.";
  }
  return "Privacy notice. Processing mode is not configured. No face recognition, no biometric identification, no emotion detection, and no speaker identification are performed. Use synthetic/demo recordings unless authorization and consent are in place.";
}

export function privacyMethodNote(mode: DeploymentMode): string {
  if (mode === "hosted")
    return "This installation runs on Vercel (frontend) and Render (backend). Media is uploaded via HTTPS to the Render instance, processed there, and stored in the configured instance filesystem/SQLite database.";
  if (mode === "local")
    return "This installation runs through the local Docker backend using the configured data directory (volume-mounted). No media leaves this machine unless explicitly exported by the user.";
  return "Deployment mode is not configured. Processing and storage behavior is unconfirmed. Verify VITE_DEPLOYMENT_MODE before interpreting any data-location claim.";
}
