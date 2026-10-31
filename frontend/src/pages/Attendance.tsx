import {
  AlertTriangle,
  CalendarCheck2,
  CheckCircle2,
  CircleDot,
  Download,
  Link2,
  ShieldCheck,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
  UserX,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { SessionPicker } from "../components/SessionPicker";
import {
  Badge,
  Card,
  CardHeader,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  InfoNote,
  LoadingBlock,
  PageHeader,
  StateBadge,
  StatCard,
} from "../components/ui";
import { api } from "../lib/api";
import { fmtClock, fmtDuration, fmtRatio, fmtRate } from "../lib/format";
import { useAsync, useDocumentTitle } from "../lib/hooks";
import type { AttendanceSummary, RosterEntry, Track } from "../lib/types";

interface PendingMap {
  track: Track;
  roster: RosterEntry | null;
}

export function AttendancePage() {
  const { id } = useParams<{ id: string }>();
  useDocumentTitle("Attendance");

  const attendanceState = useAsync<AttendanceSummary | null>(
    () => (id ? api.attendance(id) : Promise.resolve(null)),
    [id],
  );
  const rosterState = useAsync<RosterEntry[]>(() => api.roster(), []);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [pendingMap, setPendingMap] = useState<PendingMap | null>(null);
  const [mapping, setMapping] = useState(false);
  const [mapError, setMapError] = useState<Error | null>(null);

  const [newName, setNewName] = useState("");
  const [newExternalId, setNewExternalId] = useState("");
  const [newClass, setNewClass] = useState("");
  const [rosterBusy, setRosterBusy] = useState(false);
  const [rosterError, setRosterError] = useState<string | null>(null);

  const attendance = attendanceState.data;
  const roster = rosterState.data ?? [];
  const reload = attendanceState.reload;

  const confirmMapping = async () => {
    if (!id || !pendingMap) return;
    setMapping(true);
    setMapError(null);
    try {
      await api.mapTrack(id, pendingMap.track.id, pendingMap.roster?.id ?? null, true);
      setPendingMap(null);
      setDrafts((current) => {
        const next = { ...current };
        delete next[pendingMap.track.id];
        return next;
      });
      await reload();
    } catch (caught) {
      setMapError(caught as Error);
      setPendingMap(null);
    } finally {
      setMapping(false);
    }
  };

  const addRoster = async (event: FormEvent) => {
    event.preventDefault();
    if (!newName.trim()) {
      setRosterError("Enter a name for the roster entry.");
      return;
    }
    setRosterBusy(true);
    setRosterError(null);
    try {
      await api.createRoster({
        name: newName.trim(),
        external_id: newExternalId.trim() || null,
        class_label: newClass.trim() || null,
      });
      setNewName("");
      setNewExternalId("");
      await rosterState.reload();
    } catch (caught) {
      setRosterError((caught as Error).message);
    } finally {
      setRosterBusy(false);
    }
  };

  const deleteRoster = async (entry: RosterEntry) => {
    setRosterBusy(true);
    setRosterError(null);
    try {
      await api.deleteRoster(entry.id);
      await rosterState.reload();
      await reload();
    } catch (caught) {
      setRosterError((caught as Error).message);
    } finally {
      setRosterBusy(false);
    }
  };

  if (!id) {
    return (
      <div className="animate-fade-in">
        <PageHeader
          eyebrow="Attendance"
          title="Attendance"
          description="Sustained-presence attendance for a recorded session. Detected people remain anonymous until you map a track to a roster entry."
        />
        <SessionPicker sessionId={null} basePath="/attendance" label="Choose a session" />
        <EmptyState
          icon={CalendarCheck2}
          title="Select a session"
          description="Pick a completed session above to review attendance, or open a session to upload and process media."
          action={
            <Link to="/sessions" className="btn btn-secondary">
              Browse sessions
            </Link>
          }
        />
      </div>
    );
  }

  if (attendanceState.loading && !attendance) return <LoadingBlock label="Loading attendance" />;
  if (attendanceState.error)
    return (
      <ErrorState
        error={attendanceState.error}
        onRetry={reload}
        title="Attendance unavailable"
      />
    );

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Sustained presence"
        title="Attendance"
        description={
          attendance
            ? `Present requires at least ${attendance.min_presence_sec}s of observed presence. Tracks first seen after ${fmtClock(attendance.late_after_sec)} are marked late.`
            : "Sustained-presence attendance for a recorded session."
        }
        actions={
          <>
            <Link to={`/sessions/${id}`} className="btn btn-secondary btn-sm">
              Session
            </Link>
            {attendance && attendance.tracks.length > 0 ? (
              <a href={api.attendanceCsvUrl(id)} className="btn btn-secondary btn-sm">
                <Download className="h-3.5 w-3.5" /> Attendance CSV
              </a>
            ) : null}
          </>
        }
      />

      <SessionPicker sessionId={id} basePath="/attendance" />

      {mapError ? (
        <div className="mb-5">
          <ErrorState error={mapError} title="Could not update mapping" />
        </div>
      ) : null}

      {attendanceState.loading ? <LoadingBlock label="Refreshing attendance" /> : null}

      {attendance ? (
        attendance.tracks.length === 0 ? (
          <EmptyState
            icon={CalendarCheck2}
            title="No attendance records yet"
            description="This session has no detected participant tracks. Upload a video and run analysis, or check the quality notes on the session page."
            action={
              <Link to={`/sessions/${id}`} className="btn btn-primary">
                Open session
              </Link>
            }
          />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
              <StatCard
                label="Detected"
                value={attendance.total_detected}
                hint={`${attendance.anonymous} anonymous`}
                icon={Users}
              />
              <StatCard
                label="Present"
                value={attendance.present}
                hint={`≥ ${attendance.min_presence_sec}s observed`}
                icon={CheckCircle2}
                tone="success"
              />
              <StatCard
                label="Late"
                value={attendance.late}
                hint={`first seen after ${fmtClock(attendance.late_after_sec)}`}
                icon={CircleDot}
                tone="warning"
              />
              <StatCard
                label="Unconfirmed"
                value={attendance.unconfirmed}
                hint="Insufficient evidence"
                icon={AlertTriangle}
                tone="neutral"
              />
              <StatCard
                label="Mapped"
                value={attendance.mapped}
                hint={`${attendance.uncertain} uncertain`}
                icon={UserCheck}
                tone="brand"
              />
              <StatCard
                label="Attendance rate"
                value={fmtRate(attendance.attendance_rate)}
                hint="(Present + Late) ÷ detected"
                icon={CalendarCheck2}
                tone="brand"
              />
            </div>

            {attendance.warnings.length > 0 ? (
              <div className="mt-5">
                <InfoNote tone="warning" title="Interpretation notes">
                  <ul className="list-inside list-disc space-y-1">
                    {attendance.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </InfoNote>
              </div>
            ) : null}

            <Card className="mt-5">
              <CardHeader
                title="Detected participants"
                description="Each row is an anonymous track unless you explicitly map it to a roster entry. Mapping is manual and approximate."
                action={<Badge tone="neutral">{attendance.tracks.length} tracks</Badge>}
              />
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Participant</th>
                      <th>State</th>
                      <th>Presence</th>
                      <th>First / last seen</th>
                      <th>Confidence</th>
                      <th>Head centre</th>
                      <th>Movement</th>
                      <th className="text-right">Map to roster</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attendance.tracks.map((track) => {
                      const draft = drafts[track.id] ?? track.roster_id ?? "";
                      const selected = roster.find((entry) => entry.id === draft) ?? null;
                      return (
                        <tr key={track.id}>
                          <td>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-slate-900 dark:text-white">
                                {track.display_label}
                              </span>
                              {track.roster_id ? (
                                <Badge tone="brand">Mapped</Badge>
                              ) : (
                                <Badge tone="neutral">Anonymous</Badge>
                              )}
                            </div>
                            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                              {track.samples_seen} samples · {track.identity_status}
                            </p>
                            {track.note ? (
                              <p className="mt-1 max-w-xs text-xs text-slate-500 dark:text-slate-400">
                                {track.note}
                              </p>
                            ) : null}
                          </td>
                          <td>
                            <div className="flex flex-col gap-1">
                              <StateBadge state={track.attendance_state} />
                              {track.uncertain ? (
                                <span className="text-xs text-amber-600 dark:text-amber-400">
                                  Uncertain
                                </span>
                              ) : null}
                            </div>
                          </td>
                          <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                            {fmtDuration(track.duration_sec)}
                            <span className="block text-xs text-slate-400 dark:text-slate-500">
                              of {fmtDuration(attendance.session_duration_sec)}
                            </span>
                          </td>
                          <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                            {fmtClock(track.first_seen_sec)} → {fmtClock(track.last_seen_sec)}
                          </td>
                          <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                            {fmtRatio(track.confidence_avg)}
                          </td>
                          <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                            {fmtRatio(track.head_center_ratio)}
                          </td>
                          <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                            {fmtRatio(track.movement_index)}
                          </td>
                          <td>
                            <div className="flex min-w-[210px] items-center justify-end gap-1">
                              <select
                                className="input py-1.5 text-xs"
                                aria-label={`Map ${track.display_label} to a roster entry`}
                                value={draft}
                                onChange={(event) =>
                                  setDrafts((current) => ({
                                    ...current,
                                    [track.id]: event.target.value,
                                  }))
                                }
                              >
                                <option value="">Unmapped</option>
                                {roster.map((entry) => (
                                  <option key={entry.id} value={entry.id}>
                                    {entry.name}
                                    {entry.class_label ? ` (${entry.class_label})` : ""}
                                  </option>
                                ))}
                              </select>
                              {track.roster_id ? (
                                <button
                                  type="button"
                                  className="btn btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                                  onClick={() => setPendingMap({ track, roster: null })}
                                  title="Remove mapping"
                                >
                                  <UserX className="h-3.5 w-3.5" />
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  className="btn btn-secondary btn-sm"
                                  disabled={!selected || selected.id === track.roster_id}
                                  onClick={() =>
                                    selected && setPendingMap({ track, roster: selected })
                                  }
                                >
                                  <Link2 className="h-3.5 w-3.5" /> Map
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>

            <div className="mt-5 grid gap-5 xl:grid-cols-3">
              <Card className="xl:col-span-2">
                <CardHeader
                  title="Roster"
                  description="A teacher-managed list of names. Roster entries contain no biometric data and are never inferred from the video."
                  action={<Badge tone="brand">{roster.length} entries</Badge>}
                />
                <div className="p-5">
                  <form onSubmit={addRoster} className="grid gap-3 sm:grid-cols-4">
                    <div className="sm:col-span-2">
                      <label htmlFor="roster-name" className="label">
                        Name
                      </label>
                      <input
                        id="roster-name"
                        className="input"
                        placeholder="Student or participant name"
                        value={newName}
                        onChange={(event) => setNewName(event.target.value)}
                        maxLength={120}
                      />
                    </div>
                    <div>
                      <label htmlFor="roster-external" className="label">
                        ID <span className="text-slate-400">(optional)</span>
                      </label>
                      <input
                        id="roster-external"
                        className="input"
                        placeholder="School ID"
                        value={newExternalId}
                        onChange={(event) => setNewExternalId(event.target.value)}
                        maxLength={64}
                      />
                    </div>
                    <div>
                      <label htmlFor="roster-class" className="label">
                        Class
                      </label>
                      <input
                        id="roster-class"
                        className="input"
                        placeholder="8B"
                        value={newClass}
                        onChange={(event) => setNewClass(event.target.value)}
                        maxLength={120}
                      />
                    </div>
                    <div className="sm:col-span-4 flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Add names only if your institution permits this use.
                      </p>
                      <button type="submit" className="btn btn-secondary btn-sm" disabled={rosterBusy}>
                        <UserPlus className="h-3.5 w-3.5" />
                        {rosterBusy ? "Saving…" : "Add roster entry"}
                      </button>
                    </div>
                  </form>

                  {rosterError ? (
                    <p role="alert" className="mt-3 text-sm text-rose-600 dark:text-rose-400">
                      {rosterError}
                    </p>
                  ) : null}

                  {roster.length === 0 ? (
                    <div className="mt-4 rounded-xl border border-dashed border-slate-300 p-5 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                      No roster entries yet. Anonymous tracks are still counted in attendance rates.
                    </div>
                  ) : (
                    <ul className="mt-4 divide-y divide-slate-100 rounded-xl border border-slate-200 dark:divide-slate-800 dark:border-slate-700">
                      {roster.map((entry) => (
                        <li key={entry.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-slate-900 dark:text-white">
                              {entry.name}
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              {entry.external_id ? `ID ${entry.external_id}` : "No external ID"}
                              {entry.class_label ? ` · ${entry.class_label}` : ""}
                            </p>
                          </div>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm text-rose-600 dark:text-rose-400"
                            onClick={() => deleteRoster(entry)}
                            disabled={rosterBusy}
                            aria-label={`Delete roster entry ${entry.name}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </Card>

              <InfoNote tone="info" title="How mapping works">
                <p className="flex items-start gap-2">
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    ClassMind never recognises faces. A track is a numbered, anonymous observation.
                    Mapping a track to a roster name is a manual, approximate link made by you. It
                    can be removed at any time and does not change the underlying track data.
                  </span>
                </p>
                <p className="mt-2 flex items-start gap-2">
                  <Users className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    Anonymous tracks still count toward the attendance rate, so unlabelled
                    participants do not artificially lower the result.
                  </span>
                </p>
              </InfoNote>
            </div>
          </>
        )
      ) : null}

      <ConfirmDialog
        open={pendingMap !== null}
        title={pendingMap?.roster ? "Map this track?" : "Remove this mapping?"}
        description={
          pendingMap?.roster ? (
            <p>
              Link the anonymous track <strong>{pendingMap.track.display_label}</strong> to{" "}
              <strong>{pendingMap.roster.name}</strong>? This is a manual, approximate mapping — not
              biometric identification — and can be removed later.
            </p>
          ) : (
            <p>
              Remove the manual mapping for <strong>{pendingMap?.track.display_label}</strong>? The
              track will return to an anonymous label; attendance counts are unchanged.
            </p>
          )
        }
        confirmLabel={pendingMap?.roster ? "Confirm mapping" : "Remove mapping"}
        busy={mapping}
        onConfirm={confirmMapping}
        onCancel={() => setPendingMap(null)}
      />
    </div>
  );
}
