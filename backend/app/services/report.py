"""CSV and printable HTML report generation (self-contained, offline)."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from html import escape

from ..models import Session
from ..serializers import LIMITATIONS, attendance_summary, report_out


def fmt_ts(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = int(max(0, round(seconds)))
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def fmt_short(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = int(max(0, round(seconds)))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def attendance_csv(session: Session) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "session_id",
            "session_title",
            "session_date",
            "participant",
            "identity_status",
            "roster_id",
            "state",
            "presence_seconds",
            "first_seen",
            "last_seen",
            "first_seen_seconds",
            "last_seen_seconds",
            "confidence",
            "uncertain",
            "note",
        ]
    )
    for record in sorted(session.attendance, key=lambda r: (r.first_seen_sec, r.display_name)):
        writer.writerow(
            [
                session.id,
                session.title,
                session.session_date.isoformat(),
                record.display_name,
                "mapped" if record.roster_id else "anonymous",
                record.roster_id or "",
                record.state,
                f"{record.presence_sec:.1f}",
                fmt_ts(record.first_seen_sec),
                fmt_ts(record.last_seen_sec),
                f"{record.first_seen_sec:.2f}",
                f"{record.last_seen_sec:.2f}",
                f"{record.confidence:.3f}",
                "yes" if record.uncertain else "no",
                record.note or "",
            ]
        )
    return buffer.getvalue()


def report_csv(session: Session) -> str:
    summary = attendance_summary(session)
    analytics = report_out(session).analytics
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    writer.writerow(["SESSION"])
    writer.writerow(["id", session.id])
    writer.writerow(["title", session.title])
    writer.writerow(["subject", session.subject])
    writer.writerow(["class_label", session.class_label or ""])
    writer.writerow(["date", session.session_date.isoformat()])
    writer.writerow(["status", session.status])
    writer.writerow(["demo_data", "yes" if session.is_demo else "no"])
    writer.writerow(["duration_seconds", f"{session.duration_sec or 0:.1f}"])
    writer.writerow(["min_presence_seconds", f"{session.min_presence_sec:.1f}"])
    writer.writerow(["late_after_seconds", f"{session.late_after_sec:.1f}"])
    writer.writerow(["window_seconds", f"{session.window_sec:.1f}"])
    writer.writerow(["detector", session.detector_used or ""])
    writer.writerow(["audio_method", session.audio_method or ""])
    writer.writerow(["average_engagement_proxy", analytics.average_engagement])
    writer.writerow(["engagement_confidence", analytics.engagement_confidence])
    writer.writerow(["generated_at_utc", datetime.now(timezone.utc).isoformat()])
    writer.writerow([])

    writer.writerow(["ATTENDANCE SUMMARY"])
    for key in (
        "total_detected",
        "present",
        "late",
        "unconfirmed",
        "mapped",
        "anonymous",
        "uncertain",
        "attendance_rate",
    ):
        writer.writerow([key, getattr(summary, key)])
    writer.writerow([])

    writer.writerow(["ATTENDANCE"])
    writer.writerow(
        [
            "participant",
            "identity",
            "state",
            "presence_seconds",
            "first_seen",
            "last_seen",
            "confidence",
            "uncertain",
            "note",
        ]
    )
    for record in summary.records:
        writer.writerow(
            [
                record.display_name,
                "mapped" if record.roster_id else "anonymous",
                record.state,
                f"{record.presence_sec:.1f}",
                fmt_ts(record.first_seen_sec),
                fmt_ts(record.last_seen_sec),
                f"{record.confidence:.3f}",
                "yes" if record.uncertain else "no",
                record.note or "",
            ]
        )
    writer.writerow([])

    writer.writerow(["TIME WINDOWS"])
    writer.writerow(
        [
            "window",
            "start",
            "end",
            "participants",
            "new_arrivals",
            "movement_index",
            "active_ratio",
            "audio_active_ratio",
            "engagement_proxy",
            "confidence",
            "quality",
            "warnings",
        ]
    )
    for window in analytics.windows:
        writer.writerow(
            [
                window.window_index + 1,
                fmt_ts(window.start_sec),
                fmt_ts(window.end_sec),
                window.participant_count,
                window.attendance_changes,
                window.movement_index,
                window.active_ratio,
                window.audio_active_ratio,
                window.engagement_score,
                window.engagement_confidence or "",
                window.data_quality,
                "; ".join(window.warnings_json),
            ]
        )
    writer.writerow([])

    writer.writerow(["RECOMMENDATIONS"])
    writer.writerow(["source", "priority", "category", "title", "evidence", "detail", "observed", "interpretation", "start", "end"])
    for rec in sorted(session.recommendations, key=lambda r: r.created_at):
        writer.writerow(
            [
                rec.source,
                rec.priority,
                rec.category,
                rec.title,
                rec.evidence,
                rec.detail,
                rec.observed,
                rec.interpretation,
                fmt_ts(rec.start_sec) if rec.start_sec is not None else "",
                fmt_ts(rec.end_sec) if rec.end_sec is not None else "",
            ]
        )
    writer.writerow([])

    writer.writerow(["DATA QUALITY WARNINGS"])
    for warning in analytics.warnings:
        writer.writerow([warning])
    writer.writerow([])

    writer.writerow(["LIMITATIONS"])
    for limitation in LIMITATIONS:
        writer.writerow([limitation])
    return buffer.getvalue()


def _state_class(state: str) -> str:
    return {"present": "ok", "late": "warn", "unconfirmed": "muted"}.get(state, "muted")


def html_report(session: Session) -> str:
    report = report_out(session)
    summary = report.attendance
    analytics = report.analytics
    generated = report.generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    attendance_rows = "\n".join(
        f"<tr><td>{escape(r.display_name)}</td>"
        f"<td>{'Mapped' if r.roster_id else 'Anonymous'}</td>"
        f"<td class=\"{_state_class(r.state)}\">{escape(r.state.title())}</td>"
        f"<td>{fmt_short(r.presence_sec)}</td><td>{fmt_ts(r.first_seen_sec)}</td>"
        f"<td>{fmt_ts(r.last_seen_sec)}</td><td>{r.confidence:.2f}</td>"
        f"<td>{'Yes' if r.uncertain else 'No'}</td>"
        f"<td>{escape(r.note or '')}</td></tr>"
        for r in summary.records
    ) or '<tr><td colspan="9">No attendance records.</td></tr>'

    window_rows = "\n".join(
        f"<tr><td>{w.window_index + 1}</td><td>{fmt_short(w.start_sec)}–{fmt_short(w.end_sec)}</td>"
        f"<td>{w.participant_count}</td><td>{w.attendance_changes}</td>"
        f"<td>{_num(w.movement_index)}</td><td>{_ratio_pct(w.active_ratio)}</td>"
        f"<td>{_ratio_pct(w.audio_active_ratio)}</td><td>{_num(w.engagement_score)}</td>"
        f"<td>{escape(w.engagement_confidence or '—')}</td>"
        f"<td>{escape(w.data_quality)}</td>"
        f"<td>{escape('; '.join(w.warnings_json))}</td></tr>"
        for w in analytics.windows
    ) or '<tr><td colspan="11">No analysis windows.</td></tr>'

    recommendation_blocks = "\n".join(
        f"""<article class="rec">
  <div class="rec-head"><span class="badge {escape(r.priority)}">{escape(r.priority)}</span>
  <h3>{escape(r.title)}</h3><span class="source">{escape(r.source)}</span></div>
  <p><strong>Action:</strong> {escape(r.detail)}</p>
  <p><strong>Evidence:</strong> {escape(r.evidence)}</p>
  <p><strong>Observed:</strong> {escape(r.observed)}</p>
  <p><strong>Possible interpretation:</strong> {escape(r.interpretation)}</p>
  <p class="muted">Window: {fmt_ts(r.start_sec)} – {fmt_ts(r.end_sec)} · confidence: {escape(r.confidence)}</p>
</article>"""
        for r in report.recommendations
    ) or "<p>No recommendations were generated.</p>"

    warning_items = "".join(f"<li>{escape(w)}</li>" for w in analytics.warnings) or "<li>None recorded.</li>"
    limitation_items = "".join(f"<li>{escape(item)}</li>" for item in LIMITATIONS)
    audio = analytics.audio
    movement = analytics.movement_summary

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ClassMind report — {escape(session.title)}</title>
<style>
  :root {{ --ink:#111827; --muted:#6b7280; --line:#e5e7eb; --accent:#4338ca; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; color:var(--ink); margin:0; padding:32px; background:#f9fafb; }}
  .sheet {{ max-width: 1000px; margin: 0 auto; background:#fff; padding:40px; border-radius:16px; box-shadow:0 10px 30px rgba(0,0,0,.06); }}
  h1 {{ margin:0 0 4px; font-size:26px; }} h2 {{ font-size:17px; margin-top:32px; border-bottom:1px solid var(--line); padding-bottom:8px; }}
  h3 {{ font-size:15px; margin:0; }}
  .sub {{ color:var(--muted); font-size:13px; }}
  .demo {{ display:inline-block; background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:600; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-top:18px; }}
  .card {{ border:1px solid var(--line); border-radius:12px; padding:14px; }}
  .card b {{ display:block; font-size:22px; }} .card span {{ font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; margin-top:10px; }}
  th,td {{ text-align:left; padding:7px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ background:#f3f4f6; font-size:11px; text-transform:uppercase; letter-spacing:.03em; }}
  .ok {{ color:#047857; font-weight:600; }} .warn {{ color:#b45309; font-weight:600; }} .muted {{ color:var(--muted); }}
  .rec {{ border:1px solid var(--line); border-radius:12px; padding:14px 16px; margin-top:12px; page-break-inside:avoid; }}
  .rec p {{ margin:6px 0; font-size:13px; }}
  .rec-head {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }}
  .badge {{ font-size:10px; text-transform:uppercase; padding:2px 8px; border-radius:999px; background:#eef2ff; color:#3730a3; }}
  .badge.high {{ background:#fee2e2; color:#991b1b; }} .badge.low {{ background:#f3f4f6; color:#4b5563; }}
  .source {{ margin-left:auto; font-size:10px; color:var(--muted); text-transform:uppercase; }}
  .note {{ background:#eef2ff; border-radius:12px; padding:14px; font-size:12px; margin-top:24px; }}
  ul {{ font-size:13px; }}
  @media print {{ body {{ background:#fff; padding:0; }} .sheet {{ box-shadow:none; padding:0; }} .rec {{ break-inside:avoid; }} }}
</style></head>
<body><div class="sheet">
  <h1>Session analysis report</h1>
  <p class="sub">{escape(session.title)} · {escape(session.subject)} · {session.session_date.isoformat()}
  {'<span class="demo">DEMO DATA</span>' if session.is_demo else ''}</p>
  <p class="sub">Generated {generated} · ClassMind AI · processed locally · report ID {escape(session.id)}</p>

  <div class="cards">
    <div class="card"><span>Duration</span><b>{fmt_short(session.duration_sec)}</b></div>
    <div class="card"><span>Detected tracks</span><b>{summary.total_detected}</b></div>
    <div class="card"><span>Present / Late</span><b>{summary.present} / {summary.late}</b></div>
    <div class="card"><span>Attendance rate</span><b>{_rate_pct(summary.attendance_rate)}</b></div>
    <div class="card"><span>Engagement proxy</span><b>{_num(analytics.average_engagement)}</b></div>
    <div class="card"><span>Quality</span><b>{escape(str(analytics.quality.get('score', 'unknown')).title())}</b></div>
  </div>

  <h2>Attendance</h2>
  <p class="sub">Minimum presence {session.min_presence_sec:.0f}s · late arrival window {session.late_after_sec:.0f}s · detector {escape(session.detector_used or '—')}</p>
  <table><thead><tr><th>Participant</th><th>Identity</th><th>State</th><th>Presence</th><th>First seen</th><th>Last seen</th><th>Conf.</th><th>Uncertain</th><th>Note</th></tr></thead>
  <tbody>{attendance_rows}</tbody></table>

  <h2>Time-window indicators</h2>
  <table><thead><tr><th>#</th><th>Window</th><th>People</th><th>New</th><th>Movement</th><th>Active</th><th>Audio</th><th>Proxy</th><th>Conf.</th><th>Quality</th><th>Warnings</th></tr></thead>
  <tbody>{window_rows}</tbody></table>

  <h2>Audio activity</h2>
  <p class="sub">{'Audio available' if audio.available else 'Audio unavailable'} · method {escape(audio.method or '—')} · speech-active {fmt_short(audio.speech_active_sec)} ({_ratio_pct(audio.speech_ratio)})</p>

  <h2>Movement &amp; inactivity</h2>
  <p class="sub">Tracked participants: {movement.get('tracked_participants', 0)} · mean movement index {_num(movement.get('mean_movement_index'))} · longest low-movement run {fmt_short(movement.get('longest_inactive_sec'))} · face visible ratio {_ratio_pct(movement.get('face_visible_ratio'))}</p>

  <h2>Recommendations</h2>
  {recommendation_blocks}

  <h2>Data quality warnings</h2>
  <ul>{warning_items}</ul>

  <h2>Limitations</h2>
  <ul>{limitation_items}</ul>

  <div class="note"><strong>Privacy &amp; ethics:</strong> This report was generated locally from the uploaded recording. It contains no biometric identifiers, no emotion or ability assessments, and no automated decisions about students. Attendance tracks are anonymous unless a teacher explicitly mapped them to an authorised roster.</div>
</div></body></html>"""


def _num(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _ratio_pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _rate_pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f}%"
