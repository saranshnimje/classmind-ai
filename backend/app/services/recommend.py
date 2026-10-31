"""Teaching recommendation agent: transparent rules + optional local LLM.

Every recommendation carries its evidence and time interval, and separates the
observed fact from the interpretation. Nothing here is a judgement about a
student, and no student is ever penalised automatically.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from ..config import get_config

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Suggestions are decision support for the teacher, based on approximate "
    "behavioural proxies. They are not assessments of students and must not be "
    "used to penalise anyone. Verify with your own observation."
)

DIFFICULTY_KEYWORDS = (
    "difficult",
    "confus",
    "struggl",
    "hard",
    "unclear",
    "revise",
    "revisit",
    "didn't understand",
    "did not understand",
    "not understand",
)


@dataclass
class Rec:
    category: str
    title: str
    detail: str
    evidence: str
    observed: str
    interpretation: str
    start_sec: float | None = None
    end_sec: float | None = None
    priority: str = "medium"
    confidence: str = "low"
    source: str = "rule"

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "title": self.title,
            "detail": self.detail,
            "evidence": self.evidence,
            "observed": self.observed,
            "interpretation": self.interpretation,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "priority": self.priority,
            "confidence": self.confidence,
            "source": self.source,
        }


def _fmt_ts(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    seconds = int(max(0, seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _window_label(window) -> str:
    return f"{_fmt_ts(window.start_sec)}-{_fmt_ts(window.end_sec)}"


@dataclass
class AnalyticsContext:
    duration_sec: float
    windows: list[Any]
    audio: Any
    quality: dict[str, Any]
    movement_summary: dict[str, Any]
    attendance: dict[str, Any]
    notes: str | None = None
    session_title: str = ""
    subject: str = ""
    window_sec: float = 300.0
    extra: dict[str, Any] = field(default_factory=dict)


def _series(ctx: AnalyticsContext, key: str) -> list[tuple[Any, float]]:
    out = []
    for window in ctx.windows:
        value = getattr(window, key, None)
        if value is not None:
            out.append((window, float(value)))
    return out


def rule_recommendations(ctx: AnalyticsContext) -> list[Rec]:
    recs: list[Rec] = []
    windows = ctx.windows

    # 1. Consecutive decline in the engagement proxy.
    scored = [w for w in windows if w.engagement_score is not None]
    if len(scored) >= 3:
        for i in range(len(scored) - 2):
            trio = scored[i : i + 3]
            values = [w.engagement_score for w in trio]
            if values[0] - values[-1] >= 0.12 and all(
                values[j] >= values[j + 1] - 0.01 for j in range(2)
            ):
                recs.append(
                    Rec(
                        category="engagement",
                        title="Plan a short interactive check-in",
                        detail=(
                            "Pause the current format for 2-3 minutes and ask a quick question, "
                            "run a poll, or use think-pair-share before continuing."
                        ),
                        evidence=(
                            f"Engagement proxy fell from {values[0]:.2f} to {values[-1]:.2f} "
                            f"across three consecutive windows "
                            f"({_window_label(trio[0])}, {_window_label(trio[1])}, {_window_label(trio[2])})."
                        ),
                        observed=(
                            f"Average visible movement/activity indicators declined across "
                            f"windows {trio[0].window_index + 1}-{trio[-1].window_index + 1}."
                        ),
                        interpretation=(
                            "A sustained decline may indicate reduced participation in the current "
                            "activity format. It may also reflect a quieter task or camera conditions."
                        ),
                        start_sec=trio[0].start_sec,
                        end_sec=trio[-1].end_sec,
                        priority="high",
                        confidence="medium",
                    )
                )
                break

    # 2. Limited participation opportunities (audio + visual signals required).
    audio_ratio = (
        ctx.audio.speech_ratio
        if getattr(ctx.audio, "available", False) and ctx.audio.speech_ratio is not None
        else None
    )
    scored_values = [w.engagement_score for w in scored]
    mean_score = sum(scored_values) / len(scored_values) if scored_values else None
    if audio_ratio is not None and audio_ratio < 0.12 and mean_score is not None and mean_score < 0.35:
        recs.append(
            Rec(
                category="participation",
                title="Add a discussion or small-group task",
                detail=(
                    "Try a 5-minute pair discussion or a structured group exercise, then collect "
                    "one answer per group. This creates participation opportunities without "
                    "relying on volunteers."
                ),
                evidence=(
                    f"Speech-active time was {audio_ratio * 100:.1f}% of the recording and the "
                    f"average engagement proxy was {mean_score:.2f} (0-1 scale)."
                ),
                observed="Low speech activity combined with low visible activity indicators.",
                interpretation=(
                    "Students may have had few opportunities to contribute, or the task may have "
                    "been individual/quiet. This is not evidence of disengagement."
                ),
                priority="medium",
                confidence="low",
            )
        )

    # 3. Unusually long silence.
    if getattr(ctx.audio, "available", False) and ctx.audio.intervals is not None:
        from .audio import silence_intervals

        silence = silence_intervals(ctx.audio.intervals, ctx.duration_sec)
        longest = max(silence, key=lambda s: s[1] - s[0], default=None)
        if longest and (longest[1] - longest[0]) >= max(60.0, 0.2 * ctx.duration_sec):
            length = longest[1] - longest[0]
            recs.append(
                Rec(
                    category="pacing",
                    title="Review the long silent segment",
                    detail=(
                        "Re-watch this segment and decide whether the silence was intentional "
                        "(independent work, reading, writing) or whether an explanation, prompt "
                        "or break would help."
                    ),
                    evidence=(
                        f"No speech activity (silence) detected for {length:.0f}s between "
                        f"{_fmt_ts(longest[0])} and {_fmt_ts(longest[1])}."
                    ),
                    observed=f"{length:.0f}s of continuous silence in the audio track.",
                    interpretation=(
                        "Silence can be productive. Only revisit it if it does not match the "
                        "intended teaching format."
                    ),
                    start_sec=longest[0],
                    end_sec=longest[1],
                    priority="medium",
                    confidence="medium",
                )
            )

    # 4. Attendance confirmation / mapping.
    total = ctx.attendance.get("total_detected") or 0
    unconfirmed = ctx.attendance.get("unconfirmed") or 0
    anonymous = ctx.attendance.get("anonymous") or 0
    if total and unconfirmed / total >= 0.3:
        recs.append(
            Rec(
                category="data_quality",
                title="Verify unconfirmed attendance records",
                detail=(
                    "Open the attendance table and review tracks marked Unconfirmed. Check camera "
                    "coverage and the minimum presence threshold before drawing conclusions."
                ),
                evidence=(
                    f"{unconfirmed} of {total} detected tracks were below the presence threshold "
                    "or had too few observations."
                ),
                observed=f"{unconfirmed}/{total} tracks unconfirmed.",
                interpretation=(
                    "Unconfirmed means the recording did not provide enough evidence, not that "
                    "the student was absent."
                ),
                priority="high",
                confidence="high",
            )
        )
    if anonymous:
        recs.append(
            Rec(
                category="privacy",
                title="Map anonymous tracks only where authorised",
                detail=(
                    "If your institution permits it and you have a lawful basis, map tracked "
                    "participants to roster entries from the Attendance page. Otherwise keep the "
                    "records anonymous."
                ),
                evidence=f"{anonymous} attendance record(s) are currently anonymous.",
                observed="Participant identities have not been assigned.",
                interpretation=(
                    "Anonymous tracking protects privacy; mapping is an explicit teacher action."
                ),
                priority="low",
                confidence="high",
            )
        )

    # 5. Late arrivals.
    late = ctx.attendance.get("late") or 0
    if total and late >= 2 and late / total >= 0.2:
        recs.append(
            Rec(
                category="attendance",
                title="Consider a settling-in activity",
                detail=(
                    "Start with a short recap or warm-up task so late arrivals can join without "
                    "missing core instruction."
                ),
                evidence=f"{late} of {total} tracked participants first appeared after the arrival window.",
                observed=f"{late} late-arriving tracks.",
                interpretation="Arrival timing may reflect scheduling or room transitions.",
                priority="low",
                confidence="medium",
            )
        )

    # 6. Low data quality.
    quality_warnings = ctx.quality.get("warnings") or []
    if ctx.quality.get("score") in {"poor", "partial"} and quality_warnings:
        recs.append(
            Rec(
                category="data_quality",
                title="Improve capture conditions for the next session",
                detail=(
                    "Check camera height/angle, lighting and microphone placement. A front-facing, "
                    "stable camera and a central microphone improve tracking and audio coverage."
                ),
                evidence="; ".join(quality_warnings[:3]),
                observed="Processing quality warnings were recorded for this session.",
                interpretation=(
                    "Better capture conditions produce more reliable indicators; missing data is "
                    "never treated as low engagement."
                ),
                priority="medium",
                confidence="high",
            )
        )

    # 7. Prolonged inactivity.
    longest_inactive = ctx.movement_summary.get("longest_inactive_sec") or 0
    if longest_inactive >= 120 and (ctx.movement_summary.get("tracked_participants") or 0) >= 2:
        recs.append(
            Rec(
                category="engagement",
                title="Consider a brief movement or reflection break",
                detail=(
                    "A one-minute stretch, pair share or reflection prompt can reset attention "
                    "during long sedentary segments."
                ),
                evidence=f"The longest continuous low-movement run was about {longest_inactive:.0f}s.",
                observed="Prolonged low visible movement for one or more tracked participants.",
                interpretation=(
                    "Low movement is normal during writing, reading or listening. Treat this as a "
                    "prompt to review, not as proof of disengagement."
                ),
                priority="low",
                confidence="low",
            )
        )

    # 8. Teacher's own feedback.
    if ctx.notes:
        lowered = ctx.notes.lower()
        hits = [k for k in DIFFICULTY_KEYWORDS if k in lowered]
        if hits:
            recs.append(
                Rec(
                    category="teaching",
                    title="Revisit the topic flagged in your notes",
                    detail=(
                        "Plan a short re-teach or worked example for the topic you noted, then check "
                        "understanding with a low-stakes question."
                    ),
                    evidence=f"Your session note mentions: \"{ctx.notes.strip()[:180]}\"",
                    observed="Teacher-reported difficulty in the session notes.",
                    interpretation=(
                        "Your own observation is stronger evidence than the automated proxies; "
                        "combine both when planning the next lesson."
                    ),
                    priority="high",
                    confidence="high",
                )
            )

    # 9. Positive/stable pattern (only when the data is reasonably complete).
    if mean_score is not None and mean_score >= 0.6 and ctx.quality.get("score") == "good":
        recs.append(
            Rec(
                category="engagement",
                title="Keep the current activity structure",
                detail=(
                    "The measured indicators were stable and relatively high. Keep the format and "
                    "use the same capture setup next time for comparability."
                ),
                evidence=f"Average engagement proxy {mean_score:.2f} with good processing quality.",
                observed="Stable, relatively high movement and audio activity indicators.",
                interpretation="The current format appears to support visible participation.",
                priority="low",
                confidence="medium",
            )
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: priority_order.get(r.priority, 3))
    return recs


# --------------------------------------------------------------------------
# Optional local LLM (Ollama)
# --------------------------------------------------------------------------
def ollama_status(url: str | None = None, model: str | None = None, timeout: float = 3.0) -> dict:
    cfg = get_config()
    url = (url or cfg.ollama_url).rstrip("/")
    model = model or cfg.ollama_model
    try:
        request = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
        names = [m.get("name", "") for m in payload.get("models", [])]
        available = any(name == model or name.startswith(f"{model}:") for name in names)
        return {
            "enabled": cfg.ollama_enabled,
            "reachable": True,
            "model": model,
            "model_available": available,
            "installed_models": names[:10],
            "detail": (
                "Local Ollama is reachable and the configured model is installed."
                if available
                else f"Ollama is reachable but model '{model}' is not installed."
            ),
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "enabled": cfg.ollama_enabled,
            "reachable": False,
            "model": model,
            "model_available": False,
            "installed_models": [],
            "detail": f"Local Ollama not reachable at {url}: {exc}",
        }


def _llm_context(ctx: AnalyticsContext) -> dict[str, Any]:
    return {
        "session": {
            "title": ctx.session_title,
            "subject": ctx.subject,
            "duration_sec": round(ctx.duration_sec, 1),
            "window_sec": ctx.window_sec,
            "teacher_notes": (ctx.notes or "")[:600],
        },
        "attendance_summary": ctx.attendance,
        "movement_summary": ctx.movement_summary,
        "quality": {
            "score": ctx.quality.get("score"),
            "warnings": ctx.quality.get("warnings", []),
        },
        "audio": {
            "available": getattr(ctx.audio, "available", False),
            "speech_ratio": getattr(ctx.audio, "speech_ratio", None),
            "method": getattr(ctx.audio, "method", None),
        },
        "windows": [
            {
                "index": w.window_index,
                "start_sec": w.start_sec,
                "end_sec": w.end_sec,
                "participants": w.participant_count,
                "movement_index": w.movement_index,
                "active_ratio": w.active_ratio,
                "audio_active_ratio": w.audio_active_ratio,
                "engagement_proxy": w.engagement_score,
                "confidence": w.engagement_confidence,
                "quality": w.data_quality,
                "warnings": w.warnings,
            }
            for w in ctx.windows
        ],
    }


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def generate_with_ollama(ctx: AnalyticsContext, timeout: float | None = None) -> tuple[list[Rec], str]:
    cfg = get_config()
    if not cfg.ollama_enabled:
        return [], "Local LLM is disabled in settings; rule-based suggestions were used."
    status = ollama_status(cfg.ollama_url, cfg.ollama_model)
    if not status.get("reachable") or not status.get("model_available"):
        return [], status.get("detail", "Local LLM unavailable; rule-based suggestions were used.")

    context = _llm_context(ctx)
    system = (
        "You are a teaching assistant analysing classroom session analytics. "
        "Only use the supplied numbers. Never invent measurements. Never diagnose or judge "
        "students, never infer emotions or ability, and never recommend penalties. "
        "Return strict JSON: an array of objects with keys category, title, detail, evidence, "
        "observed, interpretation, start_sec, end_sec, priority (high|medium|low), "
        "confidence (high|medium|low). Provide 2-5 items. Times must be within the session "
        "duration and evidence must cite the supplied numbers."
    )
    payload = {
        "model": cfg.ollama_model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": "Session analytics JSON:\n"
                + json.dumps(context, ensure_ascii=False)
                + "\nReturn the JSON array now.",
            },
        ],
    }
    try:
        response = _post_json(
            f"{cfg.ollama_url.rstrip('/')}/api/chat",
            payload,
            timeout or cfg.ollama_timeout_sec,
        )
    except Exception as exc:
        logger.warning("Local LLM request failed: %s", exc)
        return [], f"Local LLM request failed ({exc}); rule-based suggestions were used."

    content = (response.get("message") or {}).get("content", "")
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            parsed = parsed.get("recommendations", [])
        if not isinstance(parsed, list):
            raise ValueError("expected a JSON array")
    except (ValueError, TypeError) as exc:
        return [], f"Local LLM returned unparseable output ({exc}); rule-based suggestions were used."

    recs: list[Rec] = []
    for item in parsed[:5]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        detail = str(item.get("detail", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        observed = str(item.get("observed", "")).strip()
        interpretation = str(item.get("interpretation", "")).strip()
        if not (title and detail and evidence and observed):
            continue
        start = item.get("start_sec")
        end = item.get("end_sec")
        try:
            start = float(start) if start is not None else None
            end = float(end) if end is not None else None
        except (TypeError, ValueError):
            start = end = None
        if start is not None and not (0 <= start <= ctx.duration_sec + 1):
            start = None
        if end is not None and not (0 <= end <= ctx.duration_sec + 1):
            end = None
        priority = str(item.get("priority", "medium")).lower()
        confidence = str(item.get("confidence", "low")).lower()
        recs.append(
            Rec(
                category=str(item.get("category", "teaching"))[:48],
                title=title[:200],
                detail=detail,
                evidence=evidence,
                observed=observed,
                interpretation=interpretation or "Model-generated interpretation; verify against the evidence.",
                start_sec=start,
                end_sec=end,
                priority=priority if priority in {"high", "medium", "low"} else "medium",
                confidence=confidence if confidence in {"high", "medium", "low"} else "low",
                source="local_llm",
            )
        )
    if not recs:
        return [], "Local LLM produced no valid recommendations; rule-based suggestions were used."
    return recs, f"Generated by local model '{cfg.ollama_model}' via Ollama."


def build_recommendations(ctx: AnalyticsContext) -> tuple[list[dict], dict]:
    rules = rule_recommendations(ctx)
    llm_recs, llm_message = generate_with_ollama(ctx)
    combined = [r.as_dict() for r in llm_recs] + [r.as_dict() for r in rules]
    if llm_recs and rules:
        generated_by = "local_llm+rules"
    elif llm_recs:
        generated_by = "local_llm"
    else:
        generated_by = "rules"
    return combined, {
        "generated_by": generated_by,
        "llm_available": bool(llm_recs),
        "llm_status": llm_message,
        "disclaimer": DISCLAIMER,
    }
