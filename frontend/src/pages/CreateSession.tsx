import {
  ArrowRight,
  CalendarPlus,
  ChevronDown,
  Film,
  Info,
  Lock,
  Settings2,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Card, CardHeader, ErrorState, InfoNote, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { useAsync, useDocumentTitle } from "../lib/hooks";
import type { Settings } from "../lib/types";

function todayIso(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

export function CreateSessionPage() {
  useDocumentTitle("New session");
  const navigate = useNavigate();
  const settings = useAsync<Settings>(() => api.settings(), []);

  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("General");
  const [classLabel, setClassLabel] = useState("");
  const [sessionDate, setSessionDate] = useState(todayIso);
  const [notes, setNotes] = useState("");
  const [sampleInterval, setSampleInterval] = useState("");
  const [minPresence, setMinPresence] = useState("");
  const [lateAfter, setLateAfter] = useState("");
  const [windowSec, setWindowSec] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<Error | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const defaults = settings.data;

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    if (!title.trim()) next.title = "A session title is required.";
    if (title.trim().length > 200) next.title = "Keep the title under 200 characters.";
    if (!subject.trim()) next.subject = "A subject is required.";
    if (!sessionDate) next.sessionDate = "Choose the date the class took place.";
    if (sampleInterval && (Number(sampleInterval) < 0.5 || Number(sampleInterval) > 30)) {
      next.sampleInterval = "Sample interval must be between 0.5 and 30 seconds.";
    }
    if (minPresence && (Number(minPresence) < 1 || Number(minPresence) > 3600)) {
      next.minPresence = "Minimum presence must be between 1 and 3600 seconds.";
    }
    if (lateAfter && (Number(lateAfter) < 0 || Number(lateAfter) > 7200)) {
      next.lateAfter = "Late threshold must be between 0 and 7200 seconds.";
    }
    if (windowSec && (Number(windowSec) < 30 || Number(windowSec) > 3600)) {
      next.windowSec = "Window length must be between 30 and 3600 seconds.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        title: title.trim(),
        subject: subject.trim(),
        session_date: sessionDate,
      };
      if (classLabel.trim()) payload.class_label = classLabel.trim();
      if (notes.trim()) payload.notes = notes.trim();
      if (sampleInterval) payload.sample_interval_sec = Number(sampleInterval);
      if (minPresence) payload.min_presence_sec = Number(minPresence);
      if (lateAfter) payload.late_after_sec = Number(lateAfter);
      if (windowSec) payload.window_sec = Number(windowSec);
      const session = await api.createSession(payload);
      navigate(`/sessions/${session.id}?upload=1`);
    } catch (caught) {
      setSubmitError(caught as Error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Recorded analysis"
        title="New session"
        description="Create a container for one class recording. After saving, upload the video or audio file and run analysis locally."
        actions={
          <Link to="/sessions" className="btn btn-secondary">
            Cancel
          </Link>
        }
      />

      <form onSubmit={submit} className="grid gap-5 lg:grid-cols-3" noValidate>
        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardHeader
              title="Session details"
              description="Only the title and date are required. Nothing here is shared externally."
            />
            <div className="grid gap-4 p-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label htmlFor="title" className="label">
                  Session title <span className="text-rose-500">*</span>
                </label>
                <input
                  id="title"
                  className="input"
                  placeholder="e.g. Grade 8 Science — Photosynthesis"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  aria-invalid={Boolean(errors.title)}
                  maxLength={200}
                  autoFocus
                />
                {errors.title ? (
                  <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">{errors.title}</p>
                ) : null}
              </div>

              <div>
                <label htmlFor="subject" className="label">
                  Subject <span className="text-rose-500">*</span>
                </label>
                <input
                  id="subject"
                  className="input"
                  placeholder="Science"
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                  aria-invalid={Boolean(errors.subject)}
                  maxLength={120}
                />
                {errors.subject ? (
                  <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">{errors.subject}</p>
                ) : null}
              </div>

              <div>
                <label htmlFor="class-label" className="label">
                  Class / group <span className="text-slate-400">(optional)</span>
                </label>
                <input
                  id="class-label"
                  className="input"
                  placeholder="e.g. 8B"
                  value={classLabel}
                  onChange={(event) => setClassLabel(event.target.value)}
                  maxLength={120}
                />
              </div>

              <div>
                <label htmlFor="session-date" className="label">
                  Class date <span className="text-rose-500">*</span>
                </label>
                <input
                  id="session-date"
                  type="date"
                  className="input"
                  value={sessionDate}
                  onChange={(event) => setSessionDate(event.target.value)}
                  aria-invalid={Boolean(errors.sessionDate)}
                />
                {errors.sessionDate ? (
                  <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                    {errors.sessionDate}
                  </p>
                ) : null}
              </div>

              <div>
                <span className="label">Media type</span>
                <div className="flex h-[42px] items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3.5 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300">
                  <Film className="h-4 w-4 text-slate-400" />
                  Video, audio, or both
                </div>
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="notes" className="label">
                  Notes <span className="text-slate-400">(optional)</span>
                </label>
                <textarea
                  id="notes"
                  className="input min-h-[96px] resize-y"
                  placeholder="Lesson context, camera placement, or anything that helps interpret the results."
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  maxLength={4000}
                />
                <p className="help">Stored locally with the session. Do not include sensitive student information.</p>
              </div>
            </div>
          </Card>

          <Card>
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4">
                <div>
                  <p className="flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-white">
                    <Settings2 className="h-4 w-4 text-slate-400" />
                    Analysis thresholds
                  </p>
                  <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
                    Optional overrides for this session only.
                  </p>
                </div>
                <ChevronDown className="h-4 w-4 shrink-0 text-slate-400 transition group-open:rotate-180" />
              </summary>
              <div className="grid gap-4 border-t border-slate-100 p-5 sm:grid-cols-2 dark:border-slate-800">
                <div>
                  <label htmlFor="sample-interval" className="label">
                    Frame sample interval (seconds)
                  </label>
                  <input
                    id="sample-interval"
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="30"
                    className="input"
                    placeholder={`Workspace default: ${defaults?.sample_interval_sec ?? 2}`}
                    value={sampleInterval}
                    onChange={(event) => setSampleInterval(event.target.value)}
                  />
                  {errors.sampleInterval ? (
                    <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                      {errors.sampleInterval}
                    </p>
                  ) : (
                    <p className="help">Lower values are more precise but slower to process.</p>
                  )}
                </div>
                <div>
                  <label htmlFor="min-presence" className="label">
                    Minimum presence (seconds)
                  </label>
                  <input
                    id="min-presence"
                    type="number"
                    step="1"
                    min="1"
                    max="3600"
                    className="input"
                    placeholder={`Workspace default: ${defaults?.min_presence_sec ?? 30}`}
                    value={minPresence}
                    onChange={(event) => setMinPresence(event.target.value)}
                  />
                  {errors.minPresence ? (
                    <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                      {errors.minPresence}
                    </p>
                  ) : (
                    <p className="help">Tracks below this observed time stay unconfirmed.</p>
                  )}
                </div>
                <div>
                  <label htmlFor="late-after" className="label">
                    Late after (seconds)
                  </label>
                  <input
                    id="late-after"
                    type="number"
                    step="1"
                    min="0"
                    max="7200"
                    className="input"
                    placeholder={`Workspace default: ${defaults?.late_after_sec ?? 300}`}
                    value={lateAfter}
                    onChange={(event) => setLateAfter(event.target.value)}
                  />
                  {errors.lateAfter ? (
                    <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                      {errors.lateAfter}
                    </p>
                  ) : (
                    <p className="help">First seen after this offset from the session start is marked late.</p>
                  )}
                </div>
                <div>
                  <label htmlFor="window-sec" className="label">
                    Engagement window (seconds)
                  </label>
                  <input
                    id="window-sec"
                    type="number"
                    step="30"
                    min="30"
                    max="3600"
                    className="input"
                    placeholder={`Workspace default: ${defaults?.window_sec ?? 300}`}
                    value={windowSec}
                    onChange={(event) => setWindowSec(event.target.value)}
                  />
                  {errors.windowSec ? (
                    <p className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
                      {errors.windowSec}
                    </p>
                  ) : (
                    <p className="help">Length of each reporting window in analytics.</p>
                  )}
                </div>
              </div>
            </details>
          </Card>

          {submitError ? <ErrorState error={submitError} title="Could not create session" /> : null}

          <div className="flex flex-wrap items-center justify-end gap-2">
            <Link to="/sessions" className="btn btn-secondary">
              Cancel
            </Link>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Creating…" : "Create session"}
              {!submitting ? <ArrowRight className="h-4 w-4" /> : null}
            </button>
          </div>
        </div>

        <aside className="space-y-5">
          <Card>
            <CardHeader title="What happens next" />
            <ol className="space-y-4 p-5 text-sm text-slate-600 dark:text-slate-300">
              {[
                {
                  title: "Upload media",
                  text: "Choose a video file and/or a separate audio recording. Files are validated and copied into the local data directory.",
                },
                {
                  title: "Run local analysis",
                  text: "OpenCV and an optional YOLO detector estimate anonymous people tracks; audio VAD measures speech activity.",
                },
                {
                  title: "Review and export",
                  text: "Check attendance, windowed engagement proxies and evidence-linked suggestions, then download a report.",
                },
              ].map((step, index) => (
                <li key={step.title} className="flex gap-3">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-bold text-brand-700 dark:bg-brand-500/15 dark:text-brand-300">
                    {index + 1}
                  </span>
                  <div>
                    <p className="font-semibold text-slate-900 dark:text-white">{step.title}</p>
                    <p className="mt-0.5 leading-relaxed">{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Card>

          <InfoNote tone="info" title="Privacy by design">
            <p className="flex items-start gap-2">
              <Lock className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Recordings never leave this machine. ClassMind does not perform face recognition and
                does not create biometric templates. Detected people are anonymous until you
                manually map a track to a roster entry.
              </span>
            </p>
          </InfoNote>

          <InfoNote tone="warning" title="Before you record">
            <p className="flex items-start gap-2">
              <Info className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Obtain the consent required by your school or institution, inform participants, and
                avoid capturing identifiable faces where possible. Use recordings only for the
                purpose you explained.
              </span>
            </p>
          </InfoNote>

          <Card className="p-4 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            <p className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-200">
              <CalendarPlus className="h-3.5 w-3.5" /> Supported media
            </p>
            <p className="mt-1.5">
              {defaults
                ? `Video: ${defaults.limits.video_extensions.join(", ")} · Audio: ${defaults.limits.audio_extensions.join(", ")} · Max ${defaults.limits.max_upload_mb} MB per file.`
                : "Common video and audio formats are supported. Upload limits are shown on the session page."}
            </p>
          </Card>
        </aside>
      </form>
    </div>
  );
}
