import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  FlaskConical,
  Gauge,
  HardDrive,
  Save,
  Server,
  ShieldCheck,
  Sparkles,
  Trash2,
  Waves,
} from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import {
  Badge,
  Card,
  CardHeader,
  ConfirmDialog,
  ErrorState,
  InfoNote,
  KeyValue,
  LoadingBlock,
  PageHeader,
} from "../components/ui";
import { api } from "../lib/api";
import { fmtDateTime } from "../lib/format";
import { useAsync, useDocumentTitle } from "../lib/hooks";
import type { Health, ModelsStatus, Settings } from "../lib/types";

interface FormState {
  minPresence: string;
  sampleInterval: string;
  windowSec: string;
  lateAfter: string;
  detectorBackend: string;
  ollamaEnabled: boolean;
  ollamaUrl: string;
  ollamaModel: string;
  retentionDays: string;
  deleteMedia: boolean;
}

function toForm(settings: Settings): FormState {
  return {
    minPresence: String(settings.min_presence_sec),
    sampleInterval: String(settings.sample_interval_sec),
    windowSec: String(settings.window_sec),
    lateAfter: String(settings.late_after_sec),
    detectorBackend: settings.detector_backend,
    ollamaEnabled: settings.ollama_enabled,
    ollamaUrl: settings.ollama_url,
    ollamaModel: settings.ollama_model,
    retentionDays: String(settings.retention_days),
    deleteMedia: settings.delete_media_after_processing,
  };
}

function ModelStatus({ models }: { models: ModelsStatus }) {
  return (
    <div className="space-y-4 p-5">
      <div>
        <p className="flex items-center justify-between gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <span className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-slate-400" /> Person detector
          </span>
          <Badge tone={models.detector.active === "none" ? "warning" : "success"}>
            {models.detector.active}
          </Badge>
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
          {models.detector.note}
        </p>
        <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
          Requested: {models.detector.requested} · YOLO installed:{" "}
          {models.detector.yolo_installed ? "yes" : "no"} · weights present:{" "}
          {models.detector.yolo_weights_present ? "yes" : "no"}
        </p>
      </div>
      <div className="border-t border-slate-100 pt-3 dark:border-slate-800">
        <p className="flex items-center justify-between gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <span className="flex items-center gap-2">
            <Waves className="h-4 w-4 text-slate-400" /> Audio VAD
          </span>
          <Badge tone="success">{models.audio_vad.active}</Badge>
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
          {models.audio_vad.note}
        </p>
      </div>
      <div className="border-t border-slate-100 pt-3 dark:border-slate-800">
        <p className="flex items-center justify-between gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <span className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-slate-400" /> Local LLM
          </span>
          <Badge tone={models.llm.reachable ? "success" : models.llm.enabled ? "warning" : "neutral"}>
            {models.llm.reachable ? "reachable" : models.llm.enabled ? "unreachable" : "disabled"}
          </Badge>
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
          {models.llm.detail}
        </p>
        <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
          Model: {models.llm.model}
          {models.llm.installed_models.length > 0
            ? ` · installed: ${models.llm.installed_models.join(", ")}`
            : ""}
        </p>
      </div>
    </div>
  );
}

export function SettingsPage() {
  useDocumentTitle("Settings");
  const settingsState = useAsync<Settings>(() => api.settings(), []);
  const healthState = useAsync<Health>(() => api.health(), []);
  const [form, setForm] = useState<FormState | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<Error | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [retentionBusy, setRetentionBusy] = useState(false);
  const [retentionMessage, setRetentionMessage] = useState<string | null>(null);
  const [retentionError, setRetentionError] = useState<Error | null>(null);
  const [confirmRetention, setConfirmRetention] = useState(false);

  const settings = settingsState.data;

  useEffect(() => {
    if (settings) setForm(toForm(settings));
  }, [settings]);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => (current ? { ...current, [key]: value } : current));
    setSavedAt(null);
  };

  const validate = (state: FormState): boolean => {
    const next: Record<string, string> = {};
    const check = (key: keyof FormState, min: number, max: number, label: string) => {
      const raw = state[key];
      const value = Number(raw);
      if (raw === "" || Number.isNaN(value) || value < min || value > max) {
        next[key] = `${label} must be between ${min} and ${max}.`;
      }
    };
    check("minPresence", 1, 3600, "Minimum presence");
    check("sampleInterval", 0.5, 30, "Sample interval");
    check("windowSec", 30, 3600, "Window length");
    check("lateAfter", 0, 7200, "Late threshold");
    check("retentionDays", 0, 3650, "Retention days");
    if (!/^https?:\/\/.+/i.test(state.ollamaUrl.trim())) {
      next.ollamaUrl = "Enter a full http:// or https:// URL.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!form) return;
    setSaveError(null);
    if (!validate(form)) return;
    setSaving(true);
    try {
      const updated = await api.updateSettings({
        min_presence_sec: Number(form.minPresence),
        sample_interval_sec: Number(form.sampleInterval),
        window_sec: Number(form.windowSec),
        late_after_sec: Number(form.lateAfter),
        detector_backend: form.detectorBackend,
        ollama_enabled: form.ollamaEnabled,
        ollama_url: form.ollamaUrl.trim(),
        ollama_model: form.ollamaModel.trim(),
        retention_days: Number(form.retentionDays),
        delete_media_after_processing: form.deleteMedia,
      });
      settingsState.setData(updated);
      setSavedAt(new Date().toISOString());
    } catch (caught) {
      setSaveError(caught as Error);
    } finally {
      setSaving(false);
    }
  };

  const applyRetention = async () => {
    setRetentionBusy(true);
    setRetentionError(null);
    setRetentionMessage(null);
    try {
      const result = await api.applyRetention();
      setRetentionMessage(
        result.removed_sessions === 0
          ? "No sessions were old enough to remove."
          : `Removed ${result.removed_sessions} session(s) past the retention window.`,
      );
      setConfirmRetention(false);
    } catch (caught) {
      setRetentionError(caught as Error);
      setConfirmRetention(false);
    } finally {
      setRetentionBusy(false);
    }
  };

  if (settingsState.loading && !settings)
    return <LoadingBlock label="Loading settings" />;
  if (settingsState.error)
    return (
      <ErrorState
        error={settingsState.error}
        onRetry={settingsState.reload}
        title="Settings unavailable"
      />
    );
  if (!settings || !form) return null;

  const health = healthState.data;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Local workspace"
        title="Settings"
        description="Defaults for new sessions, optional local model connections and data-retention controls. Changes apply to future analysis."
        actions={
          <Link to="/about" className="btn btn-secondary btn-sm">
            <ShieldCheck className="h-3.5 w-3.5" /> Privacy notes
          </Link>
        }
      />

      {saveError ? (
        <div className="mb-5">
          <ErrorState error={saveError} title="Could not save settings" />
        </div>
      ) : null}
      {savedAt ? (
        <div className="mb-5">
          <InfoNote tone="success" title="Settings saved">
            <p>
              Updated {fmtDateTime(savedAt)}. New sessions and analyses use these values; existing
              sessions keep the thresholds they were processed with.
            </p>
          </InfoNote>
        </div>
      ) : null}

      <form onSubmit={save} className="grid gap-5 xl:grid-cols-3" noValidate>
        <div className="space-y-5 xl:col-span-2">
          <Card>
            <CardHeader
              title="Analysis defaults"
              description="Applied to newly created sessions unless overridden per session."
            />
            <div className="grid gap-4 p-5 sm:grid-cols-2">
              <div>
                <label htmlFor="set-min-presence" className="label">
                  Minimum presence (seconds)
                </label>
                <input
                  id="set-min-presence"
                  type="number"
                  step="1"
                  min="1"
                  max="3600"
                  className="input"
                  value={form.minPresence}
                  onChange={(event) => update("minPresence", event.target.value)}
                />
                {errors.minPresence ? (
                  <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                    {errors.minPresence}
                  </p>
                ) : (
                  <p className="help">Observed time needed before a track counts as present.</p>
                )}
              </div>
              <div>
                <label htmlFor="set-late-after" className="label">
                  Late after (seconds)
                </label>
                <input
                  id="set-late-after"
                  type="number"
                  step="1"
                  min="0"
                  max="7200"
                  className="input"
                  value={form.lateAfter}
                  onChange={(event) => update("lateAfter", event.target.value)}
                />
                {errors.lateAfter ? (
                  <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                    {errors.lateAfter}
                  </p>
                ) : (
                  <p className="help">Offset from session start used for the late rule.</p>
                )}
              </div>
              <div>
                <label htmlFor="set-window" className="label">
                  Engagement window (seconds)
                </label>
                <input
                  id="set-window"
                  type="number"
                  step="30"
                  min="30"
                  max="3600"
                  className="input"
                  value={form.windowSec}
                  onChange={(event) => update("windowSec", event.target.value)}
                />
                {errors.windowSec ? (
                  <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                    {errors.windowSec}
                  </p>
                ) : (
                  <p className="help">Length of each analytics reporting window.</p>
                )}
              </div>
              <div>
                <label htmlFor="set-sample" className="label">
                  Frame sample interval (seconds)
                </label>
                <input
                  id="set-sample"
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="30"
                  className="input"
                  value={form.sampleInterval}
                  onChange={(event) => update("sampleInterval", event.target.value)}
                />
                {errors.sampleInterval ? (
                  <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                    {errors.sampleInterval}
                  </p>
                ) : (
                  <p className="help">Lower values sample more frames and take longer.</p>
                )}
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="set-detector" className="label">
                  Detector backend
                </label>
                <select
                  id="set-detector"
                  className="input"
                  value={form.detectorBackend}
                  onChange={(event) => update("detectorBackend", event.target.value)}
                >
                  <option value="auto">Auto (prefer YOLO when installed)</option>
                  <option value="yolo">YOLO only</option>
                  <option value="hog">OpenCV HOG fallback</option>
                  <option value="none">None (audio-only / testing)</option>
                </select>
                <p className="help">
                  The active backend is resolved when processing starts. Detector changes affect new
                  analyses only.
                </p>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Local language model (optional)"
              description="Ollama is used only to phrase suggestions. Rules always provide the evidence and a deterministic fallback."
            />
            <div className="space-y-4 p-5">
              <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  checked={form.ollamaEnabled}
                  onChange={(event) => update("ollamaEnabled", event.target.checked)}
                />
                <span className="text-sm text-slate-700 dark:text-slate-200">
                  <span className="font-medium">Enable local Ollama suggestions</span>
                  <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                    No cloud API keys are used. If Ollama is unreachable, ClassMind falls back to
                    rule-based suggestions and labels the source.
                  </span>
                </span>
              </label>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="ollama-url" className="label">
                    Ollama URL
                  </label>
                  <input
                    id="ollama-url"
                    className="input"
                    value={form.ollamaUrl}
                    onChange={(event) => update("ollamaUrl", event.target.value)}
                    placeholder="http://127.0.0.1:11434"
                    disabled={!form.ollamaEnabled}
                  />
                  {errors.ollamaUrl ? (
                    <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                      {errors.ollamaUrl}
                    </p>
                  ) : null}
                </div>
                <div>
                  <label htmlFor="ollama-model" className="label">
                    Model name
                  </label>
                  <input
                    id="ollama-model"
                    className="input"
                    value={form.ollamaModel}
                    onChange={(event) => update("ollamaModel", event.target.value)}
                    placeholder="llama3.2"
                    disabled={!form.ollamaEnabled}
                  />
                  <p className="help">Must already be pulled in your local Ollama installation.</p>
                </div>
              </div>

              <div className="rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-500 dark:bg-slate-800/50 dark:text-slate-400">
                <p className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-200">
                  <Server className="h-3.5 w-3.5" /> Current connection
                </p>
                <p className="mt-1">{settings.models.llm.detail}</p>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Data retention"
              description="ClassMind stores media and results locally. Retention is applied at startup and when settings are saved."
            />
            <div className="space-y-4 p-5">
              <div className="sm:w-56">
                <label htmlFor="retention-days" className="label">
                  Keep sessions for (days)
                </label>
                <input
                  id="retention-days"
                  type="number"
                  step="1"
                  min="0"
                  max="3650"
                  className="input"
                  value={form.retentionDays}
                  onChange={(event) => update("retentionDays", event.target.value)}
                />
                {errors.retentionDays ? (
                  <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                    {errors.retentionDays}
                  </p>
                ) : (
                  <p className="help">0 disables automatic removal.</p>
                )}
              </div>

              <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  checked={form.deleteMedia}
                  onChange={(event) => update("deleteMedia", event.target.checked)}
                />
                <span className="text-sm text-slate-700 dark:text-slate-200">
                  <span className="font-medium">Delete original media after processing</span>
                  <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                    Keeps derived results but removes the uploaded video/audio. You cannot re-run
                    analysis after this without uploading again.
                  </span>
                </span>
              </label>

              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {retentionMessage ? <p className="text-emerald-700 dark:text-emerald-400">{retentionMessage}</p> : null}
                  {retentionError ? (
                    <p className="text-rose-600 dark:text-rose-400">{retentionError.message}</p>
                  ) : null}
                  {!retentionMessage && !retentionError ? (
                    <p>Remove expired sessions now without waiting for the next startup.</p>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setConfirmRetention(true)}
                  disabled={retentionBusy}
                >
                  <Trash2 className="h-3.5 w-3.5" /> Apply retention now
                </button>
              </div>
            </div>
          </Card>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <button type="button" className="btn btn-secondary" onClick={() => setForm(toForm(settings))}>
              Reset changes
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              <Save className="h-4 w-4" />
              {saving ? "Saving…" : "Save settings"}
            </button>
          </div>
        </div>

        <aside className="space-y-5">
          <Card>
            <CardHeader
              title="Active components"
              description="Resolved on this machine."
              action={<Cpu className="h-4 w-4 text-slate-400" />}
            />
            <ModelStatus models={settings.models} />
          </Card>

          <Card>
            <CardHeader title="Storage & limits" description="Where data lives and what is accepted." />
            <dl className="divide-y divide-slate-100 px-5 py-2 dark:divide-slate-800">
              <KeyValue
                label="Data directory"
                value={<span className="break-all text-xs">{settings.data_dir}</span>}
              />
              <KeyValue
                label="Database"
                value={<span className="break-all text-xs">{settings.database_path}</span>}
              />
              <KeyValue label="Max upload" value={`${settings.limits.max_upload_mb} MB`} />
              <KeyValue
                label="Max duration"
                value={`${Math.round(settings.limits.max_media_duration_sec / 60)} min`}
              />
              <KeyValue label="Max frames" value={settings.limits.max_analysis_frames} />
              <KeyValue
                label="Analysis width"
                value={`${settings.limits.analysis_max_width}px`}
              />
            </dl>
            <div className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <p className="font-semibold text-slate-700 dark:text-slate-200">Accepted formats</p>
              <p className="mt-1 break-words">
                Video: {settings.limits.video_extensions.join(", ")}
              </p>
              <p className="break-words">Audio: {settings.limits.audio_extensions.join(", ")}</p>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Backend health"
              description="Local diagnostics."
              action={
                health ? (
                  <Badge tone={health.status === "ok" ? "success" : "warning"}>{health.status}</Badge>
                ) : null
              }
            />
            <div className="p-5">
              {healthState.error ? (
                <p className="text-sm text-rose-600 dark:text-rose-400">
                  {healthState.error.message}
                </p>
              ) : health ? (
                <dl className="divide-y divide-slate-100 dark:divide-slate-800">
                  <KeyValue label="Version" value={health.version} />
                  <KeyValue label="Database" value={health.database} />
                  <KeyValue
                    label="Data writable"
                    value={
                      health.data_dir_writable ? (
                        <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Yes
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400">
                          <AlertTriangle className="h-3.5 w-3.5" /> No
                        </span>
                      )
                    }
                  />
                  <KeyValue
                    label="FFmpeg"
                    value={health.ffmpeg.available ? "Available" : "Not found"}
                  />
                  <KeyValue label="Detector" value={health.detector.active} />
                  <KeyValue label="VAD" value={health.audio_vad.active} />
                </dl>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">Checking…</p>
              )}
            </div>
          </Card>

          <InfoNote tone="info" title="Local only">
            <p className="flex items-start gap-2">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                The backend binds to your machine and stores everything under the data directory.
                Nothing is sent to a cloud service. If you enable Ollama, prompts go only to the
                local URL you configure.
              </span>
            </p>
          </InfoNote>

          <Card className="p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
              <FlaskConical className="h-4 w-4 text-slate-400" /> Demo data
            </p>
            <p className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Simulated demo sessions can be added or removed from the dashboard. They are always
              labelled and never included in your own recordings.
            </p>
            <Link to="/" className="btn btn-ghost btn-sm mt-2 w-full justify-between">
              Open dashboard <Database className="h-3.5 w-3.5" />
            </Link>
          </Card>
        </aside>
      </form>

      <ConfirmDialog
        open={confirmRetention}
        title="Apply retention now?"
        description={
          <p>
            Sessions older than <strong>{form.retentionDays} days</strong> will be permanently
            deleted, including their local media and results. If retention is set to 0, nothing will
            be removed.
          </p>
        }
        confirmLabel="Apply retention"
        busy={retentionBusy}
        onConfirm={applyRetention}
        onCancel={() => setConfirmRetention(false)}
      />

      <div className="mt-6 flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
        <HardDrive className="h-3.5 w-3.5" />
        Storage usage is managed by your operating system; ClassMind does not upload or replicate
        data.
      </div>
    </div>
  );
}
