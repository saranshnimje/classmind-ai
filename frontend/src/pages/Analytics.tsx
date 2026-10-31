import {
  Activity,
  AlertTriangle,
  ArrowRight,
  AudioLines,
  Download,
  FileText,
  Gauge,
  Info,
  Microscope,
  TrendingDown,
  TrendingUp,
  Users,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import {
  WindowEngagementChart,
  WindowParticipationChart,
} from "../components/charts";
import { SessionPicker } from "../components/SessionPicker";
import {
  Badge,
  Card,
  CardHeader,
  ChartCard,
  EmptyState,
  ErrorState,
  InfoNote,
  LoadingBlock,
  PageHeader,
  StatCard,
} from "../components/ui";
import { api } from "../lib/api";
import { fmtClock, fmtDuration, fmtRatio, fmtRate } from "../lib/format";
import { useAsync, useDocumentTitle } from "../lib/hooks";
import type { Analytics, AnalysisWindow } from "../lib/types";

function qualityTone(quality: string): "success" | "warning" | "danger" | "neutral" {
  if (quality === "good") return "success";
  if (quality === "partial") return "warning";
  if (quality === "poor") return "danger";
  return "neutral";
}

function windowAt(analytics: Analytics, index: number | null): AnalysisWindow | null {
  if (index === null) return null;
  return analytics.windows.find((window) => window.window_index === index) ?? null;
}

function MethodologyRow({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div className="py-2 text-sm">
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </dt>
      <dd className="mt-0.5 leading-relaxed text-slate-700 dark:text-slate-300">{value}</dd>
    </div>
  );
}

export function AnalyticsPage() {
  const { id } = useParams<{ id: string }>();
  useDocumentTitle("Engagement analytics");

  const { data, loading, error, reload } = useAsync<Analytics | null>(
    () => (id ? api.analytics(id) : Promise.resolve(null)),
    [id],
  );

  if (!id) {
    return (
      <div className="animate-fade-in">
        <PageHeader
          eyebrow="Windowed signals"
          title="Engagement analytics"
          description="Windowed movement, active presence and speech activity. Engagement is a descriptive proxy, not a measure of learning or attention."
        />
        <SessionPicker sessionId={null} basePath="/analytics" label="Choose a session" />
        <EmptyState
          icon={Activity}
          title="Select a session"
          description="Choose a completed session above to explore its analysis windows."
          action={
            <Link to="/sessions" className="btn btn-secondary">
              Browse sessions
            </Link>
          }
        />
      </div>
    );
  }

  if (loading && !data) return <LoadingBlock label="Loading analytics" />;
  if (error)
    return (
      <ErrorState error={error} onRetry={reload} title="Analytics unavailable" />
    );
  if (!data) return null;

  const peak = windowAt(data, data.peak_window);
  const lowest = windowAt(data, data.lowest_window);
  const movement = data.movement_summary;
  const methodology = data.methodology.engagement_proxy ?? {};
  const attendance = data.attendance_summary;
  const audio = data.audio;
  const faceVisibleRatio =
    typeof data.quality.face_visible_ratio === "number" ? data.quality.face_visible_ratio : null;
  const qualityRows: Array<[string, unknown]> = [
    ["Detector", data.quality.detector],
    ["Sampled frames", data.quality.sampled_frames],
    ["Mean brightness", data.quality.brightness_mean],
    ["Camera motion", data.quality.camera_motion],
    ["Face visible", fmtRatio(faceVisibleRatio)],
    ["Audio available", data.quality.audio_available ? "Yes" : "No"],
  ];

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Windowed signals"
        title="Engagement analytics"
        description={
          data.windows.length > 0
            ? `${data.windows.length} ${data.windows.length === 1 ? "window" : "windows"} of ${Math.round(data.window_sec)}s. Missing indicators are reported as unavailable, never as low engagement.`
            : "Windowed movement, active presence and speech activity."
        }
        actions={
          <>
            <Link to={`/sessions/${id}`} className="btn btn-secondary btn-sm">
              Session
            </Link>
            <a
              href={api.reportUrl(id, "html")}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary btn-sm"
            >
              <FileText className="h-3.5 w-3.5" /> Report
            </a>
            <a href={api.reportUrl(id, "csv")} className="btn btn-secondary btn-sm">
              <Download className="h-3.5 w-3.5" /> CSV
            </a>
          </>
        }
      />

      <SessionPicker sessionId={id} basePath="/analytics" />

      {data.windows.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No analysis windows"
          description="This session does not have windowed results. Upload media and run analysis, or review the quality notes on the session page."
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
              label="Average engagement"
              value={fmtRatio(data.average_engagement)}
              hint="Descriptive 0–1 proxy"
              icon={Activity}
              tone="brand"
            />
            <StatCard
              label="Confidence"
              value={data.engagement_confidence ?? "—"}
              hint="Based on data coverage"
              icon={Gauge}
              tone="neutral"
            />
            <StatCard
              label="Peak window"
              value={peak ? `#${peak.window_index + 1}` : "—"}
              hint={peak ? `${fmtClock(peak.start_sec)} · ${fmtRatio(peak.engagement_score)}` : "No scored window"}
              icon={TrendingUp}
              tone="success"
            />
            <StatCard
              label="Lowest window"
              value={lowest ? `#${lowest.window_index + 1}` : "—"}
              hint={lowest ? `${fmtClock(lowest.start_sec)} · ${fmtRatio(lowest.engagement_score)}` : "No scored window"}
              icon={TrendingDown}
              tone="warning"
            />
            <StatCard
              label="Speech activity"
              value={fmtRatio(audio.speech_ratio)}
              hint={audio.available ? `${fmtDuration(audio.speech_active_sec)} active` : "No audio analysed"}
              icon={AudioLines}
              tone="neutral"
            />
            <StatCard
              label="Participants"
              value={movement.tracked_participants ?? "—"}
              hint={`Mean movement ${fmtRatio(movement.mean_movement_index ?? null)}`}
              icon={Users}
              tone="brand"
            />
          </div>

          {data.warnings.length > 0 ? (
            <div className="mt-5">
              <InfoNote tone="warning" title="Data-quality warnings">
                <ul className="list-inside list-disc space-y-1">
                  {data.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </InfoNote>
            </div>
          ) : null}

          <div className="mt-5 grid gap-5 xl:grid-cols-2">
            <ChartCard
              title="Engagement over time"
              description="Per-window engagement proxy. Dashed lines mark the 35% and 60% descriptive bands."
              footnote="Scores combine observed movement, active presence and speech activity where available. Windows with insufficient visual data are left empty rather than scored as zero."
            >
              <WindowEngagementChart windows={data.windows} />
            </ChartCard>
            <ChartCard
              title="Participants and movement"
              description="People visible in each window and the movement index on a 0–100% scale."
              footnote="Movement is frame-difference activity after accounting for camera motion. It is a coarse signal, not a judgement of behaviour."
            >
              <WindowParticipationChart windows={data.windows} />
            </ChartCard>
          </div>

          <Card className="mt-5">
            <CardHeader
              title="Window detail"
              description="Every window, including quality flags and the indicators that were actually available."
              action={<Badge tone="neutral">{data.windows.length} windows</Badge>}
            />
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Window</th>
                    <th>Interval</th>
                    <th>Participants</th>
                    <th>Engagement</th>
                    <th>Confidence</th>
                    <th>Quality</th>
                    <th>Movement</th>
                    <th>Active</th>
                    <th>Looking away</th>
                    <th>Speech</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {data.windows.map((window) => (
                    <tr key={window.window_index}>
                      <td className="whitespace-nowrap font-medium text-slate-900 dark:text-white">
                        #{window.window_index + 1}
                      </td>
                      <td className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                        {fmtClock(window.start_sec)} → {fmtClock(window.end_sec)}
                      </td>
                      <td className="text-slate-600 dark:text-slate-300">{window.participant_count}</td>
                      <td className="whitespace-nowrap font-semibold text-slate-900 dark:text-white">
                        {fmtRatio(window.engagement_score)}
                      </td>
                      <td className="whitespace-nowrap">
                        {window.engagement_confidence ? (
                          <Badge
                            tone={
                              window.engagement_confidence === "high"
                                ? "success"
                                : window.engagement_confidence === "medium"
                                  ? "warning"
                                  : "neutral"
                            }
                          >
                            {window.engagement_confidence}
                          </Badge>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        <Badge tone={qualityTone(window.data_quality)}>{window.data_quality}</Badge>
                      </td>
                      <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                        {fmtRatio(window.movement_index)}
                      </td>
                      <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                        {fmtRatio(window.active_ratio)}
                      </td>
                      <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                        {fmtRatio(window.looking_away_ratio)}
                      </td>
                      <td className="whitespace-nowrap text-slate-600 dark:text-slate-300">
                        {fmtRatio(window.audio_active_ratio)}
                      </td>
                      <td className="max-w-xs text-xs text-slate-500 dark:text-slate-400">
                        {window.warnings_json.length > 0 ? (
                          <ul className="list-inside list-disc space-y-0.5">
                            {window.warnings_json.map((warning) => (
                              <li key={warning}>{warning}</li>
                            ))}
                          </ul>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="mt-5 grid gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader
                title="Audio activity"
                description="Speech-active intervals detected by the local voice-activity detector."
                action={
                  audio.available ? (
                    <Badge tone="success">{audio.method ?? "VAD"}</Badge>
                  ) : (
                    <Badge tone="neutral">Unavailable</Badge>
                  )
                }
              />
              <div className="space-y-4 p-5">
                {audio.available ? (
                  <>
                    <div className="grid gap-3 sm:grid-cols-3">
                      <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                        <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Speech ratio
                        </p>
                        <p className="mt-1 text-lg font-bold text-slate-900 dark:text-white">
                          {fmtRatio(audio.speech_ratio)}
                        </p>
                      </div>
                      <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                        <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Speech active
                        </p>
                        <p className="mt-1 text-lg font-bold text-slate-900 dark:text-white">
                          {fmtDuration(audio.speech_active_sec)}
                        </p>
                      </div>
                      <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                        <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Intervals
                        </p>
                        <p className="mt-1 text-lg font-bold text-slate-900 dark:text-white">
                          {audio.interval_count}
                        </p>
                      </div>
                    </div>

                    {audio.intervals.length > 0 ? (
                      <div>
                        <div className="flex h-7 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                          {audio.intervals.slice(0, 300).map((interval, index) => {
                            const total = audio.intervals.reduce(
                              (sum, item) => sum + (item.end_sec - item.start_sec),
                              0,
                            );
                            const width = total > 0 ? ((interval.end_sec - interval.start_sec) / total) * 100 : 0;
                            return (
                              <div
                                key={`${interval.start_sec}-${interval.kind}-${index}`}
                                className={
                                  interval.kind === "speech"
                                    ? "bg-brand-500"
                                    : "bg-slate-300 dark:bg-slate-700"
                                }
                                style={{ width: `${width}%` }}
                                title={`${fmtClock(interval.start_sec)}–${fmtClock(interval.end_sec)} · ${interval.kind}`}
                              />
                            );
                          })}
                        </div>
                        <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                          <span className="flex items-center gap-1.5">
                            <span className="h-2.5 w-2.5 rounded-full bg-brand-500" /> Speech
                          </span>
                          <span className="flex items-center gap-1.5">
                            <span className="h-2.5 w-2.5 rounded-full bg-slate-300 dark:bg-slate-700" />{" "}
                            Silence / no speech
                          </span>
                          {audio.intervals.length > 300 ? (
                            <span>Showing the first 300 of {audio.intervals.length} intervals.</span>
                          ) : null}
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        No speech intervals were detected in this recording.
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                    No usable audio track was analysed for this session. Speech activity is therefore
                    missing — this is not evidence of low engagement. Visual indicators are reported
                    independently.
                  </p>
                )}

                {audio.warnings.length > 0 ? (
                  <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                    <p className="mb-1 flex items-center gap-1.5 font-semibold">
                      <AlertTriangle className="h-3.5 w-3.5" /> Audio notes
                    </p>
                    <ul className="list-inside list-disc space-y-0.5">
                      {audio.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            </Card>

            <Card>
              <CardHeader title="Attendance snapshot" description="From the same session." />
              <div className="space-y-2 p-5 text-sm">
                {[
                  ["Detected", attendance.total_detected, ""],
                  ["Present", attendance.present, ""],
                  ["Late", attendance.late, ""],
                  ["Unconfirmed", attendance.unconfirmed, ""],
                  ["Mapped", attendance.mapped, ""],
                ].map(([label, value]) => (
                  <div key={String(label)} className="flex justify-between border-b border-slate-100 py-1.5 last:border-0 dark:border-slate-800">
                    <span className="text-slate-500 dark:text-slate-400">{label}</span>
                    <span className="font-semibold text-slate-900 dark:text-white">
                      {value ?? "—"}
                    </span>
                  </div>
                ))}
                <div className="flex justify-between pt-2">
                  <span className="text-slate-500 dark:text-slate-400">Attendance rate</span>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {fmtRate(attendance.attendance_rate ?? null)}
                  </span>
                </div>
                <Link
                  to={`/attendance/${id}`}
                  className="btn btn-secondary btn-sm mt-3 w-full justify-between"
                >
                  Review attendance <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </Card>
          </div>

          <div className="mt-5 grid gap-5 xl:grid-cols-2">
            <Card>
              <CardHeader
                title="How engagement is calculated"
                description="Transparent methodology, shown exactly as applied to this session."
                action={<Microscope className="h-4 w-4 text-slate-400" />}
              />
              <dl className="divide-y divide-slate-100 px-5 py-2 dark:divide-slate-800">
                <MethodologyRow label="Definition" value={methodology.definition} />
                <MethodologyRow label="Formula" value={methodology.formula} />
                <MethodologyRow label="Movement index" value={methodology.movement_index} />
                <MethodologyRow label="Active ratio" value={methodology.active_ratio} />
                <MethodologyRow label="Missing data policy" value={methodology.missing_data_policy} />
                <MethodologyRow
                  label="Window"
                  value={methodology.window_sec ? `${methodology.window_sec}s` : undefined}
                />
                <MethodologyRow
                  label="Sample interval"
                  value={
                    methodology.sample_interval_sec
                      ? `${methodology.sample_interval_sec}s`
                      : undefined
                  }
                />
              </dl>
              {methodology.confidence_rules ? (
                <div className="border-t border-slate-100 px-5 py-3 text-sm dark:border-slate-800">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Confidence rules
                  </p>
                  <ul className="mt-1 space-y-1 text-slate-600 dark:text-slate-300">
                    {Object.entries(methodology.confidence_rules).map(([key, value]) => (
                      <li key={key}>
                        <span className="font-medium capitalize">{key}:</span> {value}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </Card>

            <Card>
              <CardHeader
                title="Data quality & limitations"
                description="What the pipeline could observe in this recording."
                action={
                  typeof data.quality.score === "string" ? (
                    <Badge tone={qualityTone(data.quality.score)}>{data.quality.score}</Badge>
                  ) : null
                }
              />
              <div className="space-y-4 p-5">
                <dl className="grid gap-3 sm:grid-cols-2">
                  {qualityRows.map(([label, value]) => (
                    <div key={String(label)} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <dt className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        {label}
                      </dt>
                      <dd className="mt-1 text-sm font-semibold text-slate-900 dark:text-white">
                        {value === null || value === undefined || value === ""
                          ? "—"
                          : typeof value === "number"
                            ? value.toFixed(2)
                            : String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>

                <div className="rounded-xl border border-slate-200 p-3 text-xs leading-relaxed text-slate-600 dark:border-slate-700 dark:text-slate-300">
                  <p className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-200">
                    <Info className="h-3.5 w-3.5" /> Head orientation
                  </p>
                  <p className="mt-1">
                    {data.methodology.head_orientation?.method ??
                      "Approximate head-position estimate from frontal-face detection."}
                  </p>
                  <p className="mt-1">
                    {data.methodology.head_orientation?.limitations ??
                      "Not a gaze tracker. Side profiles and obscured faces are reported as unknown."}
                  </p>
                </div>

                <div className="rounded-xl border border-slate-200 p-3 text-xs leading-relaxed text-slate-600 dark:border-slate-700 dark:text-slate-300">
                  <p className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-200">
                    <AudioLines className="h-3.5 w-3.5" /> Audio method
                  </p>
                  <p className="mt-1">
                    {data.methodology.audio?.method ?? "Local voice-activity detection."}
                  </p>
                  <p className="mt-1">
                    {data.methodology.audio?.limitations ??
                      "Speech activity is not the same as student participation and may include teacher speech."}
                  </p>
                </div>

                <div className="text-xs text-slate-500 dark:text-slate-400">
                  <p className="font-semibold text-slate-700 dark:text-slate-200">Movement summary</p>
                  <p className="mt-1">
                    Longest inactive stretch {fmtDuration(movement.longest_inactive_sec ?? null)} ·
                    total inactive {fmtDuration(movement.total_inactive_sec ?? null)} · inactive
                    participants {movement.inactive_participants ?? "—"} · face visible{" "}
                    {fmtRatio(movement.face_visible_ratio ?? null)}
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
