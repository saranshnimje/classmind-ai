import {
  ArrowRight,
  CalendarDays,
  Film,
  PlusCircle,
  Search,
  Trash2,
  Users,
  Video,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  Badge,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageHeader,
  StatusBadge,
} from "../components/ui";
import { api } from "../lib/api";
import { fmtDate, fmtDuration, fmtRatio, fmtFileSize } from "../lib/format";
import { useAsync, useDocumentTitle } from "../lib/hooks";
import type { Session } from "../lib/types";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "created", label: "Created" },
  { value: "uploaded", label: "Media ready" },
  { value: "queued", label: "Queued" },
  { value: "processing", label: "Processing" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
];

export function SessionsPage() {
  useDocumentTitle("Sessions");
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [status, setStatus] = useState("");
  const [includeDemo, setIncludeDemo] = useState(true);
  const [pendingDelete, setPendingDelete] = useState<Session | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<Error | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [query]);

  const { data, loading, error, reload } = useAsync<Session[]>(
    () =>
      api.listSessions({
        status: status || undefined,
        q: debouncedQuery || undefined,
        includeDemo,
      }),
    [status, debouncedQuery, includeDemo],
  );

  const sessions = data ?? [];
  const hasFilters = Boolean(query || status || !includeDemo);

  const remove = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteSession(pendingDelete.id);
      setPendingDelete(null);
      await reload();
    } catch (caught) {
      setDeleteError(caught as Error);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Recorded sessions"
        title="Sessions"
        description="Each session holds one classroom recording and its locally computed attendance and engagement results."
        actions={
          <Link to="/sessions/new" className="btn btn-primary">
            <PlusCircle className="h-4 w-4" />
            New session
          </Link>
        }
      />

      <Card className="mb-5 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
          <div className="flex-1">
            <label htmlFor="session-search" className="label">
              Search
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                id="session-search"
                type="search"
                className="input pl-9"
                placeholder="Search by session title…"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
          </div>
          <div className="sm:w-52">
            <label htmlFor="session-status" className="label">
              Status
            </label>
            <select
              id="session-status"
              className="input"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 pb-2.5 text-sm text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              checked={includeDemo}
              onChange={(event) => setIncludeDemo(event.target.checked)}
            />
            Include demo sessions
          </label>
        </div>
      </Card>

      {deleteError ? (
        <div className="mb-5">
          <ErrorState error={deleteError} title="Could not delete session" />
        </div>
      ) : null}

      {loading && !data ? <LoadingBlock label="Loading sessions" /> : null}
      {error ? <ErrorState error={error} onRetry={reload} title="Sessions unavailable" /> : null}

      {!loading && !error && sessions.length === 0 ? (
        hasFilters ? (
          <EmptyState
            icon={Search}
            title="No sessions match these filters"
            description="Try a different search term or clear the status filter."
            action={
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setQuery("");
                  setStatus("");
                  setIncludeDemo(true);
                }}
              >
                Clear filters
              </button>
            }
          />
        ) : (
          <EmptyState
            icon={Video}
            title="No sessions yet"
            description="Create a session to upload a classroom video or audio recording. You can also load simulated demo data from the dashboard."
            action={
              <Link to="/sessions/new" className="btn btn-primary">
                <PlusCircle className="h-4 w-4" />
                Create a session
              </Link>
            }
          />
        )
      ) : null}

      {sessions.length > 0 ? (
        <Card>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Media</th>
                  <th>Tracks</th>
                  <th>Engagement</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id}>
                    <td>
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to={`/sessions/${session.id}`}
                          className="font-semibold text-slate-900 hover:text-brand-700 dark:text-white dark:hover:text-brand-300"
                        >
                          {session.title}
                        </Link>
                        {session.is_demo ? <Badge tone="demo">Demo data</Badge> : null}
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        {session.subject}
                        {session.class_label ? ` · ${session.class_label}` : ""}
                      </p>
                      {session.status === "failed" && session.error_message ? (
                        <p className="mt-1 max-w-sm text-xs text-rose-600 dark:text-rose-400">
                          {session.error_message}
                        </p>
                      ) : null}
                    </td>
                    <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                      <span className="flex items-center gap-1.5">
                        <CalendarDays className="h-3.5 w-3.5 text-slate-400" />
                        {fmtDate(session.session_date)}
                      </span>
                    </td>
                    <td>
                      <StatusBadge status={session.status} />
                    </td>
                    <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                      <span className="flex items-center gap-1.5">
                        <Film className="h-3.5 w-3.5" />
                        {session.video_filename ? fmtDuration(session.duration_sec) : "No video"}
                      </span>
                      <span className="mt-0.5 block">
                        {session.video_filename
                          ? fmtFileSize(session.video_size_bytes)
                          : session.audio_filename
                            ? "Audio only"
                            : "—"}
                        {session.has_audio ? " · audio" : ""}
                      </span>
                    </td>
                    <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                      <span className="flex items-center gap-1.5">
                        <Users className="h-3.5 w-3.5 text-slate-400" />
                        {session.track_count}
                      </span>
                    </td>
                    <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                      {fmtRatio(session.average_engagement)}
                    </td>
                    <td>
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          to={`/sessions/${session.id}`}
                          className="btn btn-ghost btn-sm"
                          aria-label={`Open ${session.title}`}
                        >
                          Open <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm text-rose-600 hover:bg-rose-50 hover:text-rose-700 dark:text-rose-400 dark:hover:bg-rose-950/40"
                          onClick={() => setPendingDelete(session)}
                          aria-label={`Delete ${session.title}`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete this session?"
        description={
          <>
            <p>
              <strong>{pendingDelete?.title}</strong> and its local media, attendance records and
              analysis results will be permanently deleted from this machine.
            </p>
            <p className="mt-2">This cannot be undone.</p>
          </>
        }
        confirmLabel="Delete session"
        busy={deleting}
        onConfirm={remove}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
