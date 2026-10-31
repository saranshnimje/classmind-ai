"""Sustained-presence attendance logic.

A tracked person is only marked Present/Late when the track persists for at
least the configured minimum duration. Otherwise the result is Unconfirmed.
Anonymous tracks are never silently matched to a real student.
"""

from __future__ import annotations

from dataclasses import dataclass

from .vision import TrackResult


@dataclass
class AttendanceDecision:
    state: str
    note: str
    uncertain: bool
    presence_sec: float


def decide_attendance(
    track: TrackResult,
    *,
    min_presence_sec: float,
    late_after_sec: float,
) -> AttendanceDecision:
    presence = round(track.duration_sec, 3)

    if track.samples_seen < 2:
        return AttendanceDecision(
            state="unconfirmed",
            note=(
                "Only one sampled observation; presence cannot be confirmed. "
                "This is not evidence of absence."
            ),
            uncertain=True,
            presence_sec=presence,
        )

    if presence < min_presence_sec:
        return AttendanceDecision(
            state="unconfirmed",
            note=(
                f"Tracked for {presence:.0f}s, below the {min_presence_sec:.0f}s "
                "minimum presence threshold."
            ),
            uncertain=track.uncertain,
            presence_sec=presence,
        )

    if late_after_sec > 0 and track.first_seen > late_after_sec:
        state = "late"
        note = (
            f"First tracked {track.first_seen:.0f}s into the session "
            f"(after the {late_after_sec:.0f}s arrival window)."
        )
    else:
        state = "present"
        note = f"Sustained presence for {presence:.0f}s."

    if track.uncertain:
        note += " Detection confidence is low, so treat this record as uncertain."

    return AttendanceDecision(
        state=state,
        note=note,
        uncertain=track.uncertain,
        presence_sec=presence,
    )


def summarize(records: list[dict]) -> dict:
    total = len(records)
    present = sum(1 for r in records if r["state"] == "present")
    late = sum(1 for r in records if r["state"] == "late")
    unconfirmed = sum(1 for r in records if r["state"] == "unconfirmed")
    mapped = sum(1 for r in records if r.get("roster_id"))
    uncertain = sum(1 for r in records if r.get("uncertain"))
    confirmed = present + late
    return {
        "total_detected": total,
        "present": present,
        "late": late,
        "unconfirmed": unconfirmed,
        "mapped": mapped,
        "anonymous": total - mapped,
        "uncertain": uncertain,
        "attendance_rate": round(confirmed / total * 100, 2) if total else None,
    }
