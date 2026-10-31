"""Analytics, recommendations and report exports."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..errors import ApiError
from ..schemas import AnalyticsOut, RecommendationOut, RecommendationResponse, ReportOut
from ..serializers import analytics_out, report_out
from ..services.report import html_report, report_csv
from ..services.recommend import DISCLAIMER
from .sessions import get_session_or_404

router = APIRouter(tags=["analytics"])


def _require_results(session) -> None:
    if not session.windows and not session.attendance:
        raise ApiError(
            409,
            "not_ready",
            "This session has no analysis results yet. Upload media and run processing first.",
        )


def _slug(title: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()[:60] or "session"


@router.get("/sessions/{session_id}/analytics", response_model=AnalyticsOut)
def get_analytics(session_id: str, db: DbSession = Depends(get_db)) -> AnalyticsOut:
    session = get_session_or_404(db, session_id)
    return analytics_out(session)


@router.get(
    "/sessions/{session_id}/recommendations", response_model=RecommendationResponse
)
def get_recommendations(
    session_id: str, db: DbSession = Depends(get_db)
) -> RecommendationResponse:
    session = get_session_or_404(db, session_id)
    quality = session.quality_json or {}
    meta = quality.get("recommendation_meta") or {}
    recs = [RecommendationOut.model_validate(r) for r in session.recommendations]
    llm_recs = [r for r in recs if r.source == "local_llm"]
    if recs:
        generated_by = meta.get("generated_by") or (
            "local_llm+rules" if llm_recs else "rules"
        )
        llm_status = meta.get(
            "llm_status",
            "Local model suggestions are present." if llm_recs else "Rule-based suggestions.",
        )
    else:
        generated_by = "none"
        llm_status = (
            "No recommendations yet. Process this session to generate rule-based suggestions."
            if session.status != "completed"
            else "No rule conditions matched this session's data."
        )
    return RecommendationResponse(
        session_id=session.id,
        generated_by=generated_by,
        llm_available=bool(llm_recs),
        llm_status=llm_status,
        disclaimer=DISCLAIMER,
        recommendations=recs,
    )


@router.get("/sessions/{session_id}/report", response_model=ReportOut)
def get_report(session_id: str, db: DbSession = Depends(get_db)) -> ReportOut:
    session = get_session_or_404(db, session_id)
    _require_results(session)
    return report_out(session)


@router.get("/sessions/{session_id}/report.html")
def get_report_html(
    session_id: str,
    db: DbSession = Depends(get_db),
    download: bool = Query(default=False),
) -> Response:
    session = get_session_or_404(db, session_id)
    _require_results(session)
    headers = {}
    if download:
        headers["Content-Disposition"] = (
            f'attachment; filename="classmind-{_slug(session.title)}-report.html"'
        )
    return Response(
        content=html_report(session),
        media_type="text/html; charset=utf-8",
        headers=headers,
    )


@router.get("/sessions/{session_id}/report.csv")
def get_report_csv(session_id: str, db: DbSession = Depends(get_db)) -> Response:
    session = get_session_or_404(db, session_id)
    _require_results(session)
    return Response(
        content=report_csv(session),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="classmind-{_slug(session.title)}-report.csv"'
        },
    )
