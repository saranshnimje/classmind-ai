import {
  Activity,
  ArrowRight,
  CalendarCheck2,
  Database,
  FlaskConical,
  Gauge,
  PlusCircle,
  Sparkles,
  Trash2,
  Users,
  Video,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  EngagementTrendChart,
  SessionVolumeChart,
} from "../components/charts";
import {
  Badge,
  Card,
  CardHeader,
  ChartCard,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  InfoNote,
  LoadingBlock,
  PageHeader,
  StatCard,
  StatusBadge,
} from "../components/ui";
import { api } from "../lib/api";
import { fmtDate, fmtDuration, fmtRate, fmtRatio, relativeTime } from "../lib/format";
import { useAsync, useDocumentTitle } from "../lib/hooks";
import type { Dashboard as DashboardData } from "../lib/types";

export function DashboardPage() {
  useDocumentTitle("Dashboard");
  const { data, loading, error, reload } = useAsync<DashboardData>(() => api.dashboard(), []);
  const [busy, setBusy] = useState<"seed" | "clear" | null>(null);
  const [actionError, setActionError] = useState<Error | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);

  const seedDemo = async () => {
    setBusy("seed");
    setActionError(null);
    try {
      await api.seedDemo();
      await reload();
    } catch (caught) {
      setActionError(caught as Error);
    } finally {
      setBusy(null);
    }
  };

  const clearDemo = async () => {
    setBusy("clear");
    setActionError(null);
    try {
      await api.clearDemo();
      setConfirmClear(false);
      await reload();
    } catch (caught) {
      setActionError(caught as Error);
    } finally {
      setBusy(null);
    }
  };

  if (loading && !data) return <LoadingBlock label="Loading dashboard" />;
  if (error) return <ErrorState error={error} onRetry={reload} title="Dashboard unavailable" />;
  if (!data) return null;

  const hasDemo = data.recent_sessions.some((session) => session.is_demo);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Classroom overview"
        title="Dashboard"
        description={(() => {
          const mode = (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE;
          const isHosted = typeof mode === "string" && mode.trim().toLowerCase() === "hosted";
          return isHosted ? "Attendance and engagement signals from recordings processed on the Render backend." : "Attendance and engagement signals from recordings processed on this machine. Values are descriptive proxies, not student assessments.";
        })()}
        actions={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={seedDemo}
              disabled={busy !== null}
            >
              <FlaskConical className="h-4 w-4" />
              {busy === "seed" ? "Seeding…" : "Load demo data"}
            </button>
            <Link to="/sessions/new" className="btn btn-primary">
              <PlusCircle className="h-4 w-4" />
              New session
            </Link>
          </>
        }
      />

      {actionError ? (
        <div className="mb-5">
          <ErrorState error={actionError} title="Action failed" />
        </div>
      ) : null}

      {data.processing.active ? (
        <div className="mb-5">
          <InfoNote tone="info" title="Analysis in progress">
            <p>
              {data.processing.active_jobs} job(s) queued or running. You can keep browsing; results
              appear when processing finishes.
            </p>
          </InfoNote>
        </div>
      ) : null}

      {hasDemo ? (
        <div className="mb-5">
          <InfoNote tone="warning" title="Demo data is present">
            <p>
              Sessions marked <strong>Demo data</strong> are simulated examples for exploring the
              interface. They are never mixed into your own recordings and are labelled throughout
              the app.
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm mt-2"
              onClick={() => setConfirmClear(true)}
              disabled={busy !== null}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Remove demo data
            </button>
          </InfoNote>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="Sessions"
          value={data.total_sessions}
          hint={`${data.completed_sessions} completed`}
          icon={Video}
        />
        <StatCard
          label="Attendance records"
          value={data.total_attendance_records}
          hint="Across completed analyses"
          icon={Users}
          tone="success"
        />
        <StatCard
          label="Average attendance"
          value={fmtRate(data.average_attendance_rate)}
          hint="(Present + Late) ÷ detected"
          icon={CalendarCheck2}
          tone="warning"
        />
        <StatCard
          label="Average engagement"
          value={fmtRatio(data.average_engagement)}
          hint="Descriptive 0–1 proxy"
          icon={Activity}
          tone="brand"
        />
        <StatCard
          label="Data location"
          value={(() => {
            const mode = (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE;
            return typeof mode === "string" && mode.trim().toLowerCase() === "hosted" ? "Hosted (Render)" : "Local";
          })()}
          hint={(() => {
            const mode = (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE;
            return typeof mode === "string" && mode.trim().toLowerCase() === "hosted" ? "Uploaded media is sent to the Render backend for processing; storage depends on instance filesystem." : "No media leaves this machine";
          })()}
          icon={Database}
          tone="neutral"
        />
      </div>

      {data.total_sessions === 0 ? (
        <div className="mt-6">
          <EmptyState
            icon={Sparkles}
            title="Start with a recording"
            description="Create a session, upload a classroom video, and ClassMind will estimate anonymous attendance and engagement windows. You can also load simulated demo data to explore the interface."
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Link to="/sessions/new" className="btn btn-primary">
                  <PlusCircle className="h-4 w-4" />
                  Create your first session
                </Link>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={seedDemo}
                  disabled={busy !== null}
                >
                  <FlaskConical className="h-4 w-4" />
                  Load demo data
                </button>
              </div>
            }
          />
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-5 xl:grid-cols-2">
            <ChartCard
              title="Engagement trend"
              description="Completed sessions, most recent last. Engagement is a 0–100% proxy."
              empty={data.engagement_trend.length === 0}
              emptyMessage="No completed sessions with engagement results yet."
              footnote={data.definitions.engagement}
            >
              <EngagementTrendChart data={data.engagement_trend} />
            </ChartCard>
            <ChartCard
              title="Sessions in the last 14 days"
              description="Session dates recorded in this workspace."
              empty={data.sessions_last_14_days.every((row) => row.sessions === 0)}
              emptyMessage="No sessions in the last 14 days."
            >
              <SessionVolumeChart data={data.sessions_last_14_days} />
            </ChartCard>
          </div>

          <div className="mt-6 grid gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader
                title="Recent sessions"
                description="Open a session to upload media, run analysis, or review results."
                action={
                  <Link to="/sessions" className="btn btn-ghost btn-sm">
                    All sessions <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                }
              />
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Session</th>
                      <th>Date</th>
                      <th>Status</th>
                      <th>Attendance</th>
                      <th>Engagement</th>
                      <th className="text-right">Open</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_sessions.map((session) => (
                      <tr key={session.id}>
                        <td>
                          <div className="flex flex-wrap items-center gap-2">
                            <Link
                              to={`/sessions/${session.id}`}
                              className="font-semibold text-slate-900 hover:text-brand-700 dark:text-white dark:hover:text-brand-300"
                            >
                              {session.title}
                            </Link>
                            {session.is_demo ? <Badge tone="demo">Demo</Badge> : null}
                          </div>
                          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                            {session.subject}
                            {session.class_label ? ` · ${session.class_label}` : ""} ·{" "}
                            {fmtDuration(session.duration_sec)}
                          </p>
                          {session.status === "failed" && session.error_message ? (
                            <p className="mt-1 max-w-xs truncate text-xs text-rose-600 dark:text-rose-400">
                              {session.error_message}
                            </p>
                          ) : null}
                        </td>
                        <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                          {fmtDate(session.session_date)}
                        </td>
                        <td>
                          <StatusBadge status={session.status} />
                        </td>
                        <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                          {fmtRate(session.attendance_rate)}
                        </td>
                        <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                          {fmtRatio(session.average_engagement)}
                        </td>
                        <td className="text-right">
                          <Link
                            to={`/sessions/${session.id}`}
                            className="btn btn-ghost btn-sm"
                            aria-label={`Open ${session.title}`}
                          >
                            <ArrowRight className="h-4 w-4" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card>
              <CardHeader title="Recent activity" description="Local system events." />
              {data.recent_events.length === 0 ? (
                <p className="px-5 py-8 text-center text-sm text-slate-500 dark:text-slate-400">
                  No activity recorded yet.
                </p>
              ) : (
                <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                  {data.recent_events.map((event) => (
                    <li key={event.id} className="flex gap-3 px-5 py-3">
                      <span
                        className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                          event.level === "error"
                            ? "bg-rose-500"
                            : event.level === "warning"
                              ? "bg-amber-500"
                              : event.level === "success"
                                ? "bg-emerald-500"
                                : "bg-brand-400"
                        }`}
                      />
                      <div className="min-w-0">
                        <p className="text-sm text-slate-700 dark:text-slate-200">{event.message}</p>
                        <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
                          {relativeTime(event.created_at)}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <Card className="p-4">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                <Gauge className="h-4 w-4" /> Detector
              </p>
              <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">
                {data.models.detector.active}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                {data.models.detector.note}
              </p>
            </Card>
            <Card className="p-4">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                <Activity className="h-4 w-4" /> Audio VAD
              </p>
              <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">
                {data.models.audio_vad.active}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                {data.models.audio_vad.note}
              </p>
            </Card>
            <Card className="p-4">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                <Sparkles className="h-4 w-4" /> Recommendations
              </p>
              <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">
                {data.models.llm.enabled ? "Local LLM + rules" : "Rules only"}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                {data.models.llm.detail}
              </p>
            </Card>
          </div>
        </>
      )}

      <ConfirmDialog
        open={confirmClear}
        title="Remove all demo sessions?"
        description="This deletes every session marked as simulated demo data, including its generated results. Your own recordings are not affected."
        confirmLabel="Remove demo data"
        busy={busy === "clear"}
        onConfirm={clearDemo}
        onCancel={() => setConfirmClear(false)}
      />
    </div>
  );
}
