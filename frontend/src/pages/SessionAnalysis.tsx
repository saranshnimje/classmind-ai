import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CalendarCheck2,
  Camera,
  CheckCircle2,
  CircleDot,
  Download,
  FileAudio,
  FileText,
  Film,
  Gauge,
  Lightbulb,
  Play,
  ShieldCheck,
  Square,
  Trash2,
  Upload,
  Video,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { rememberSession } from "../components/Layout";
import {
  Badge,
  Card,
  CardHeader,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  InfoNote,
  KeyValue,
  LoadingBlock,
  PageHeader,
  ProgressBar,
  StatCard,
  StatusBadge,
} from "../components/ui";
import { api } from "../lib/api";
import {
  DEFAULT_AUDIO_EXTENSIONS,
  DEFAULT_VIDEO_EXTENSIONS,
  fmtClock,
  fmtDateTime,
  fmtDuration,
  fmtFileSize,
  fmtRatio,
  fmtRate,
  validateMediaFile,
} from "../lib/format";
import { useAsync, useDocumentTitle } from "../lib/hooks";
import type {
  Analytics,
  AttendanceSummary,
  LiveStatus,
  ProcessingStatus,
  SessionDetail,
  Settings,
} from "../lib/types";

interface ResultsBundle {
  attendance: AttendanceSummary;
  analytics: Analytics;
}

export function SessionAnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const highlightUpload = searchParams.get("upload") === "1";

  const sessionState = useAsync<SessionDetail>(
    () => (id ? api.getSession(id) : Promise.reject(new Error("Missing session id"))),
    [id],
  );
  const session = sessionState.data;
  const settingsState = useAsync<Settings>(() => api.settings(), []);

  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [videoKey, setVideoKey] = useState(0);
  const [audioKey, setAudioKey] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [actionError, setActionError] = useState<Error | null>(null);
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [live, setLive] = useState<LiveStatus | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [liveStarting, setLiveStarting] = useState(false);
  const [cameraIndex, setCameraIndex] = useState("0");
  const [maxSeconds, setMaxSeconds] = useState("300");

  useDocumentTitle(session?.title ?? "Session");

  useEffect(() => {
    if (id) rememberSession(id);
  }, [id]);

  const reload = sessionState.reload;
  const shouldPoll = session?.status === "queued" || session?.status === "processing";

  useEffect(() => {
    if (!id || !shouldPoll) return;
    let cancelled = false;
    let timer: number | undefined;
    const tick = async () => {
      try {
        const next = await api.getStatus(id);
        if (cancelled) return;
        setStatus(next);
        if (next.status === "completed" || next.status === "failed") {
          await reload();
          return;
        }
      } catch {
        // transient polling failure; try again
      }
      if (!cancelled) timer = window.setTimeout(tick, 2000);
    };
    void tick();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [id, shouldPoll, reload]);

  useEffect(() => {
    if (!id || !live?.active) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await api.liveStatus(id);
        setLive(next);
        if (!next.active) await reload();
      } catch {
        // ignore transient live-status errors
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [id, live?.active, reload]);

  const results = useAsync<ResultsBundle | null>(async () => {
    if (!id || session?.status !== "completed") return null;
    const [attendance, analytics] = await Promise.all([api.attendance(id), api.analytics(id)]);
    return { attendance, analytics };
  }, [id, session?.status]);

  const limits = settingsState.data?.limits ?? {
    max_upload_mb: 512,
    video_extensions: DEFAULT_VIDEO_EXTENSIONS,
    audio_extensions: DEFAULT_AUDIO_EXTENSIONS,
  };

  const pickFile = (kind: "video" | "audio", file: File | null) => {
    setUploadError(null);
    setNotice(null);
    if (!file) {
      if (kind === "video") {
        setVideoFile(null);
        setVideoKey((key) => key + 1);
      } else {
        setAudioFile(null);
        setAudioKey((key) => key + 1);
      }
      return;
    }
    const problem = validateMediaFile(file, kind, limits);
    if (problem) {
      setUploadError(problem);
      if (kind === "video") {
        setVideoFile(null);
        setVideoKey((key) => key + 1);
      } else {
        setAudioFile(null);
        setAudioKey((key) => key + 1);
      }
      return;
    }
    if (kind === "video") setVideoFile(file);
    else setAudioFile(file);
  };

  const upload = async () => {
    if (!id || (!videoFile && !audioFile)) return;
    setUploading(true);
    setUploadError(null);
    setNotice(null);
    try {
      const result = await api.uploadMedia(id, videoFile, audioFile);
      setNotice(result.message);
      setVideoFile(null);
      setAudioFile(null);
      setVideoKey((key) => key + 1);
      setAudioKey((key) => key + 1);
      await reload();
    } catch (caught) {
      setUploadError((caught as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const startProcessing = async () => {
    if (!id) return;
    setStarting(true);
    setActionError(null);
    setNotice(null);
    try {
      await api.processSession(id);
      await reload();
    } catch (caught) {
      setActionError(caught as Error);
    } finally {
      setStarting(false);
    }
  };

  const remove = async () => {
    if (!id) return;
    setDeleting(true);
    setActionError(null);
    try {
      await api.deleteSession(id);
      navigate("/sessions");
    } catch (caught) {
      setActionError(caught as Error);
      setConfirmDelete(false);
    } finally {
      setDeleting(false);
    }
  };

  const startLive = async () => {
    if (!id) return;
    setLiveStarting(true);
    setLiveError(null);
    try {
      const result = await api.startLive(id, {
        camera_index: Number(cameraIndex) || 0,
        max_seconds: Number(maxSeconds) || 300,
      });
      setLive(result);
      await reload();
    } catch (caught) {
      setLiveError((caught as Error).message);
    } finally {
      setLiveStarting(false);
    }
  };

  const stopLive = async () => {
    if (!id) return;
    setLiveError(null);
    try {
      const result = await api.stopLive(id);
      setLive(result);
      await reload();
    } catch (caught) {
      setLiveError((caught as Error).message);
    }
  };

  if (sessionState.loading && !session) return <LoadingBlock label="Loading session" />;
  if (sessionState.error)
    return (
      <ErrorState
        error={sessionState.error}
        onRetry={reload}
        title="Could not load this session"
      />
    );
  if (!session || !id) return null;

  const processing = session.status === "queued" || session.status === "processing";
  const completed = session.status === "completed";
  const failed = session.status === "failed";
  const progress = status?.progress ?? session.latest_job?.progress ?? (completed ? 100 : 0);
  const stage = status?.stage ?? session.latest_job?.stage ?? null;
  const jobMessage = status?.message ?? session.latest_job?.message ?? null;
  const qualityWarnings = Array.isArray(session.quality_json.warnings)
    ? (session.quality_json.warnings as string[])
    : [];
  const confidence = session.quality_json.engagement_confidence;

  const attendance = results.data?.attendance;
  const analytics = results.data?.analytics;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={`${session.subject}${session.class_label ? ` · ${session.class_label}` : ""}`}
        title={session.title}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <StatusBadge status={session.status} />
            {session.is_demo ? <Badge tone="demo">Demo data — simulated</Badge> : null}
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {fmtDateTime(session.session_date)}
            </span>
          </span>
        }
        actions={
          <>
            <Link to="/sessions" className="btn btn-secondary btn-sm">
              All sessions
            </Link>
            {completed ? (
              <>
                <a
                  href={api.reportUrl(id, "html")}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary btn-sm"
                >
                  <FileText className="h-3.5 w-3.5" />
                  Report
                </a>
                <a href={api.reportUrl(id, "csv")} className="btn btn-secondary btn-sm">
                  <Download className="h-3.5 w-3.5" />
                  CSV
                </a>
              </>
            ) : null}
            <button
              type="button"
              className="btn btn-secondary btn-sm text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete
            </button>
          </>
        }
      />

      {session.is_demo ? (
        <div className="mb-5">
          <InfoNote tone="warning" title="This is simulated demo data">
            <p>
              Values in this session were generated to demonstrate the interface. They are not
              derived from a real recording and should not be interpreted as classroom evidence.
            </p>
          </InfoNote>
        </div>
      ) : null}

      {failed ? (
        <div className="mb-5">
          <InfoNote tone="danger" title="Analysis failed">
            <p>{session.error_message ?? "The processing job stopped unexpectedly."}</p>
            <p className="mt-2">
              You can replace the media or retry processing. The local job log is available in the
              backend console.
            </p>
          </InfoNote>
        </div>
      ) : null}

      {actionError ? (
        <div className="mb-5">
          <ErrorState error={actionError} title="Action failed" />
        </div>
      ) : null}

      {completed ? (
        <div className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard
            label="Present"
            value={attendance ? attendance.present : "—"}
            hint={`≥ ${session.min_presence_sec}s observed`}
            icon={CheckCircle2}
            tone="success"
          />
          <StatCard
            label="Late"
            value={attendance ? attendance.late : "—"}
            hint={`first seen after ${fmtClock(session.late_after_sec)}`}
            icon={CircleDot}
            tone="warning"
          />
          <StatCard
            label="Unconfirmed"
            value={attendance ? attendance.unconfirmed : "—"}
            hint="Insufficient observed time"
            icon={AlertTriangle}
            tone="neutral"
          />
          <StatCard
            label="Attendance rate"
            value={fmtRate(attendance?.attendance_rate ?? null)}
            hint="(Present + Late) ÷ detected"
            icon={CalendarCheck2}
            tone="brand"
          />
          <StatCard
            label="Engagement proxy"
            value={fmtRatio(session.average_engagement)}
            hint={typeof confidence === "string" ? `${confidence} confidence` : "Descriptive only"}
            icon={Activity}
            tone="brand"
          />
        </div>
      ) : null}

      {completed ? (
        <Card className="mb-5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">
                Review the analysis
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Attendance mapping is manual and approximate. Engagement is a descriptive proxy.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link to={`/attendance/${id}`} className="btn btn-primary btn-sm">
                <CalendarCheck2 className="h-3.5 w-3.5" /> Attendance
              </Link>
              <Link to={`/analytics/${id}`} className="btn btn-secondary btn-sm">
                <Activity className="h-3.5 w-3.5" /> Analytics
              </Link>
              <Link to={`/recommendations/${id}`} className="btn btn-secondary btn-sm">
                <Lightbulb className="h-3.5 w-3.5" /> Recommendations
              </Link>
            </div>
          </div>
        </Card>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Card className={highlightUpload && !session.video_filename ? "ring-2 ring-brand-500" : ""}>
            <CardHeader
              title="Media"
              description="Upload a classroom video and/or a separate audio track. Files are validated locally."
              action={
                session.video_filename || session.audio_filename ? (
                  <Badge tone="success">Media ready</Badge>
                ) : (
                  <Badge tone="neutral">Not uploaded</Badge>
                )
              }
            />
            <div className="space-y-4 p-5">
              {session.video_filename || session.audio_filename ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {session.video_filename ? (
                    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        <Film className="h-3.5 w-3.5" /> Video
                      </p>
                      <p className="mt-1 truncate text-sm font-medium text-slate-900 dark:text-white">
                        {session.video_filename}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        {fmtDuration(session.duration_sec)} ·{" "}
                        {session.width && session.height
                          ? `${session.width}×${session.height}`
                          : "resolution unknown"}{" "}
                        · {session.fps ? `${session.fps.toFixed(1)} fps` : "fps unknown"} ·{" "}
                        {fmtFileSize(session.video_size_bytes)}
                      </p>
                    </div>
                  ) : null}
                  {session.audio_filename ? (
                    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        <FileAudio className="h-3.5 w-3.5" /> Audio
                      </p>
                      <p className="mt-1 truncate text-sm font-medium text-slate-900 dark:text-white">
                        {session.audio_filename}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        {fmtFileSize(session.audio_size_bytes)}
                        {session.has_audio ? " · speech analysis available" : ""}
                      </p>
                    </div>
                  ) : null}
                </div>
              ) : null}

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="video-file" className="label">
                    Video file
                  </label>
                  <input
                    key={videoKey}
                    id="video-file"
                    type="file"
                    accept={limits.video_extensions.join(",")}
                    className="block w-full cursor-pointer rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-brand-700 hover:border-brand-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300 dark:file:bg-brand-500/15 dark:file:text-brand-300"
                    onChange={(event) => pickFile("video", event.target.files?.[0] ?? null)}
                    disabled={processing}
                  />
                  {videoFile ? (
                    <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                      {videoFile.name} · {fmtFileSize(videoFile.size)}
                    </p>
                  ) : (
                    <p className="help">
                      {limits.video_extensions.join(", ")} · max {limits.max_upload_mb} MB
                    </p>
                  )}
                </div>
                <div>
                  <label htmlFor="audio-file" className="label">
                    Audio file <span className="text-slate-400">(optional)</span>
                  </label>
                  <input
                    key={audioKey}
                    id="audio-file"
                    type="file"
                    accept={limits.audio_extensions.join(",")}
                    className="block w-full cursor-pointer rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-brand-700 hover:border-brand-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300 dark:file:bg-brand-500/15 dark:file:text-brand-300"
                    onChange={(event) => pickFile("audio", event.target.files?.[0] ?? null)}
                    disabled={processing}
                  />
                  {audioFile ? (
                    <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                      {audioFile.name} · {fmtFileSize(audioFile.size)}
                    </p>
                  ) : (
                    <p className="help">
                      {limits.audio_extensions.join(", ")} · max {limits.max_upload_mb} MB
                    </p>
                  )}
                </div>
              </div>

              {uploadError ? (
                <p role="alert" className="text-sm text-rose-600 dark:text-rose-400">
                  {uploadError}
                </p>
              ) : null}
              {notice ? (
                <p role="status" className="text-sm text-emerald-700 dark:text-emerald-400">
                  {notice}
                </p>
              ) : null}

              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Uploading replaces existing media and clears previous results.
                </p>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={upload}
                  disabled={uploading || processing || (!videoFile && !audioFile)}
                >
                  <Upload className="h-4 w-4" />
                  {uploading ? "Uploading…" : "Upload media"}
                </button>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Analysis"
              description="Processing runs in the background on this machine. You can leave this page and return later."
              action={<StatusBadge status={session.status} />}
            />
            <div className="space-y-4 p-5">
              {processing ? (
                <>
                  <ProgressBar
                    value={progress}
                    label={stage ? `${stage} · ${jobMessage ?? "working"}` : "Starting analysis"}
                  />
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Sampling frames and running local detection can take a while on CPU. Large or
                    crowded recordings may need a longer sample interval.
                  </p>
                </>
              ) : completed ? (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 dark:border-emerald-900 dark:bg-emerald-950/30">
                  <div className="flex items-start gap-2 text-sm text-emerald-900 dark:text-emerald-200">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>
                      <p className="font-semibold">Analysis complete</p>
                      <p className="text-xs">
                        {session.detector_used ? `Detector: ${session.detector_used}` : "Detector unknown"}
                        {session.audio_method ? ` · Audio: ${session.audio_method}` : " · No audio analysis"}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={startProcessing}
                    disabled={starting}
                  >
                    <Play className="h-3.5 w-3.5" /> Re-run analysis
                  </button>
                </div>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="max-w-md text-sm text-slate-600 dark:text-slate-300">
                    {session.video_filename || session.audio_filename
                      ? "Media is ready. Start local analysis to estimate anonymous attendance and engagement windows."
                      : "Upload a video or audio file first. Audio-only sessions can still produce speech activity, but no visual indicators."}
                  </p>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={startProcessing}
                    disabled={starting || (!session.video_filename && !session.audio_filename)}
                  >
                    <Play className="h-4 w-4" />
                    {starting ? "Queueing…" : failed ? "Retry analysis" : "Run analysis"}
                  </button>
                </div>
              )}

              {qualityWarnings.length > 0 && (completed || failed) ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                  <p className="mb-1 flex items-center gap-1.5 font-semibold">
                    <AlertTriangle className="h-3.5 w-3.5" /> Quality notes
                  </p>
                  <ul className="list-inside list-disc space-y-0.5">
                    {qualityWarnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </Card>

          {completed ? (
            <Card>
              <CardHeader
                title="Windowed engagement"
                description="A transparent proxy blending movement, active presence and speech activity. Missing data is never treated as low engagement."
              />
              <div className="p-5">
                {analytics && analytics.windows.length > 0 ? (
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        Average engagement
                      </p>
                      <p className="mt-1 text-xl font-bold text-slate-900 dark:text-white">
                        {fmtRatio(analytics.average_engagement)}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {analytics.engagement_confidence ?? "unknown"} confidence
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        Windows analysed
                      </p>
                      <p className="mt-1 text-xl font-bold text-slate-900 dark:text-white">
                        {analytics.windows.length}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {Math.round(analytics.window_sec)}s windows
                      </p>
                    </div>
                  </div>
                ) : results.loading ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">Loading summary…</p>
                ) : (
                  <EmptyState
                    icon={Activity}
                    title="No window data"
                    description="This session completed without analysable windows."
                    action={
                      <Link to={`/analytics/${id}`} className="btn btn-secondary btn-sm">
                        Open analytics
                      </Link>
                    }
                  />
                )}
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link to={`/analytics/${id}`} className="btn btn-secondary btn-sm">
                    <Gauge className="h-3.5 w-3.5" /> Full analytics
                  </Link>
                  <a
                    href={api.reportUrl(id, "html")}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-secondary btn-sm"
                  >
                    <FileText className="h-3.5 w-3.5" /> Printable report
                  </a>
                </div>
              </div>
            </Card>
          ) : null}
        </div>

        <aside className="space-y-5">
          <Card>
            <CardHeader title="Session details" />
            <dl className="divide-y divide-slate-100 px-5 py-2 dark:divide-slate-800">
              <KeyValue label="Subject" value={session.subject} />
              <KeyValue label="Class" value={session.class_label ?? "—"} />
              <KeyValue label="Class date" value={fmtDateTime(session.session_date)} />
              <KeyValue label="Duration" value={fmtDuration(session.duration_sec)} />
              <KeyValue label="Created" value={fmtDateTime(session.created_at)} />
              <KeyValue label="Processed" value={fmtDateTime(session.processed_at)} />
              <KeyValue label="Detector" value={session.detector_used ?? "—"} />
              <KeyValue label="Audio method" value={session.audio_method ?? "—"} />
            </dl>
            {session.notes ? (
              <div className="border-t border-slate-100 px-5 py-3 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Notes
                </p>
                <p className="whitespace-pre-wrap">{session.notes}</p>
              </div>
            ) : null}
          </Card>

          <Card>
            <CardHeader
              title="Thresholds"
              description="Rules applied to this session."
            />
            <dl className="divide-y divide-slate-100 px-5 py-2 dark:divide-slate-800">
              <KeyValue label="Min. presence" value={`${session.min_presence_sec}s`} />
              <KeyValue label="Late after" value={`${session.late_after_sec}s`} />
              <KeyValue label="Window" value={`${session.window_sec}s`} />
              <KeyValue label="Sample interval" value={`${session.sample_interval_sec}s`} />
            </dl>
          </Card>

          <Card>
            <CardHeader
              title="Optional live capture"
              description="Capture directly from a local camera instead of uploading a file."
              action={<Camera className="h-4 w-4 text-slate-400" />}
            />
            <div className="space-y-3 p-5">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label htmlFor="camera-index" className="label">
                    Camera index
                  </label>
                  <input
                    id="camera-index"
                    type="number"
                    min="0"
                    max="10"
                    className="input"
                    value={cameraIndex}
                    onChange={(event) => setCameraIndex(event.target.value)}
                    disabled={Boolean(live?.active)}
                  />
                </div>
                <div>
                  <label htmlFor="max-seconds" className="label">
                    Max seconds
                  </label>
                  <input
                    id="max-seconds"
                    type="number"
                    min="5"
                    max="1800"
                    className="input"
                    value={maxSeconds}
                    onChange={(event) => setMaxSeconds(event.target.value)}
                    disabled={Boolean(live?.active)}
                  />
                </div>
              </div>

              {live?.active ? (
                <div className="rounded-xl border border-brand-200 bg-brand-50/70 p-3 text-sm dark:border-brand-900 dark:bg-brand-950/30">
                  <p className="font-semibold text-brand-900 dark:text-brand-200">
                    Recording… {live.frames} frames · {Math.round(live.seconds)}s
                  </p>
                  <p className="mt-0.5 text-xs text-brand-700 dark:text-brand-300">{live.message}</p>
                </div>
              ) : null}
              {liveError ? (
                <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">
                  {liveError}
                </p>
              ) : null}

              <div className="flex gap-2">
                {live?.active ? (
                  <button type="button" className="btn btn-danger btn-sm flex-1" onClick={stopLive}>
                    <Square className="h-3.5 w-3.5" /> Stop capture
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm flex-1"
                    onClick={startLive}
                    disabled={liveStarting || processing}
                  >
                    <Camera className="h-3.5 w-3.5" />
                    {liveStarting ? "Starting…" : "Start capture"}
                  </button>
                )}
              </div>
              <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                Requires a camera accessible to the backend process. Live capture is an optional
                convenience and has not been verified in every environment.
              </p>
            </div>
          </Card>

          <InfoNote tone="info" title="Anonymous by default">
            <p className="flex items-start gap-2">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Tracks are numbered participants, not identified students. Face recognition and
                biometric templates are not used. You may manually map a track to a roster entry on
                the attendance page.
              </span>
            </p>
          </InfoNote>

          <Card className="p-4">
            <p className="flex items-center gap-1.5 text-sm font-semibold text-slate-900 dark:text-white">
              <Video className="h-4 w-4 text-slate-400" /> Quick links
            </p>
            <div className="mt-3 flex flex-col gap-2">
              <Link to={`/attendance/${id}`} className="btn btn-ghost btn-sm justify-between">
                Attendance <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Link to={`/analytics/${id}`} className="btn btn-ghost btn-sm justify-between">
                Analytics <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Link to={`/recommendations/${id}`} className="btn btn-ghost btn-sm justify-between">
                Recommendations <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Link to="/settings" className="btn btn-ghost btn-sm justify-between">
                Workspace settings <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </Card>
        </aside>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete this session?"
        description={
          <p>
            <strong>{session.title}</strong>, its media and all computed results will be permanently
            deleted from this machine. This cannot be undone.
          </p>
        }
        confirmLabel="Delete session"
        busy={deleting}
        onConfirm={remove}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  );
}
