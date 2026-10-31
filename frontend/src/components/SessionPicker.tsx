import { ChevronDown, PlusCircle, Video } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import { fmtDate, fmtDuration } from "../lib/format";
import { useAsync } from "../lib/hooks";
import type { Session } from "../lib/types";
import { Badge, ErrorState, Spinner, StatusBadge } from "./ui";

export function SessionPicker({
  sessionId,
  basePath,
  label = "Session",
}: {
  sessionId?: string | null;
  basePath: string;
  label?: string;
}) {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync<Session[]>(() => api.listSessions(), []);
  const sessions = data ?? [];
  const current = sessions.find((session) => session.id === sessionId) ?? null;

  if (error) {
    return <ErrorState error={error} onRetry={reload} title="Could not load sessions" />;
  }

  if (!loading && sessions.length === 0) {
    return (
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-slate-100 p-2 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
            <Video className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900 dark:text-white">No sessions yet</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Create a session and upload a recording to see results here.
            </p>
          </div>
        </div>
        <Link to="/sessions/new" className="btn btn-primary btn-sm">
          <PlusCircle className="h-3.5 w-3.5" />
          New session
        </Link>
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-card dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 sm:max-w-md">
          <label htmlFor="session-picker" className="label">
            {label}
          </label>
          <div className="relative">
            <select
              id="session-picker"
              className="input appearance-none pr-10"
              value={sessionId ?? ""}
              onChange={(event) => {
                const value = event.target.value;
                if (value) navigate(`${basePath}/${value}`);
              }}
              disabled={loading}
            >
              <option value="">{loading ? "Loading sessions…" : "Select a session…"}</option>
              {sessions.map((session) => (
                <option key={session.id} value={session.id}>
                  {session.title} · {fmtDate(session.session_date)}
                  {session.is_demo ? " (demo)" : ""}
                </option>
              ))}
            </select>
            <span className="pointer-events-none absolute inset-y-0 right-3 grid place-items-center text-slate-400">
              {loading ? <Spinner /> : <ChevronDown className="h-4 w-4" />}
            </span>
          </div>
        </div>

        {current ? (
          <div className="flex flex-wrap items-center gap-2 pb-1 text-xs text-slate-500 dark:text-slate-400">
            <StatusBadge status={current.status} />
            {current.is_demo ? <Badge tone="demo">Demo data</Badge> : null}
            <span>{fmtDuration(current.duration_sec)}</span>
            {current.class_label ? <span>· {current.class_label}</span> : null}
          </div>
        ) : null}

        <Link to="/sessions/new" className="btn btn-secondary btn-sm ml-auto">
          <PlusCircle className="h-3.5 w-3.5" />
          New session
        </Link>
      </div>
    </div>
  );
}
