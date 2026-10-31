/**
 * Deployment-mode-aware privacy notice text.
 *
 * Uses VITE_DEPLOYMENT_MODE (defaults to "local" if missing/unknown).
 * Never infers hosting from import.meta.env.PROD.
 */
export function privacyNoticeText(): string {
  const raw = (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE;
  const mode = typeof raw === "string" ? raw.trim().toLowerCase() : "local";

  if (mode === "hosted") {
    return [
      "<p class='flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-200'>Hosted privacy</p>",
      "<p class='mt-1'>Frontend is hosted on Vercel. Recordings are sent over HTTPS to the Render backend for processing.</p>",
      "<p class='mt-1'>Processing and storage happen on the deployed instance.</p>",
      "<p class='mt-2 text-[11px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500'>Data location</p>",
      "<p class='px-3 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400'>Render (instance filesystem). Use synthetic/demo recordings unless authorization and consent are in place.</p>",
    ].join("");
  }

  if (mode === "local") {
    return [
      "<p class='flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-200'>Local privacy</p>",
      "<p class='mt-1'>Media stays on this machine. No face recognition, no cloud uploads, no student surveillance profiles.</p>",
      "<p class='mt-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400'>Data is stored according to the local Docker configuration.</p>",
    ].join("");
  }

  // Unknown / missing configuration: never claim unsupported local-only processing.
  return [
    "<p class='flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-200'>Privacy notice</p>",
    "<p class='mt-1'>Processing mode is not configured. No face recognition, no biometric identification, no emotion detection, and no speaker identification are performed.</p>",
    "<p class='mt-1'>Engagement scores are descriptive proxies only.</p>",
    "<p class='mt-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400'>Review deployment settings to confirm local vs hosted behavior.</p>",
  ].join("");
}
