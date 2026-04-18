from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from app.domain.report.schemas import (
    GenerateReportRequest,
    GenerateReportResponse,
    ReportSummary,
    DailySummary,
    TrendData,
    ReportHistoryResponse,
    ReportItem,
)
from app.infrastructure.database.repository import report_repo
from app.infrastructure.llm.gemini_client import generate_insight

_DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def _week_label(week_start: date) -> str:
    """날짜 → '2026년 4월 2주차' 형식"""
    week_num = (week_start.day - 1) // 7 + 1
    return f"{week_start.year}년 {week_start.month}월 {week_num}주차"


def _build_summary(req: GenerateReportRequest) -> ReportSummary:
    sleep_mins    = [s.sleep_min for s in req.sleep]
    restless_mins = [s.restless_min for s in req.sleep]
    return ReportSummary(
        avg_sleep_h=round(sum(sleep_mins) / len(sleep_mins) / 60, 1),
        avg_restless_min=round(sum(restless_mins) / len(restless_mins)),
        cry_count=req.events.cry_count,
        leave_count=req.events.leave_count,
        temp_avg=req.environment.temp_avg,
        db_max=req.environment.db_max,
    )


def _build_daily(req: GenerateReportRequest) -> list:
    return [
        DailySummary(
            date=s.date,
            day=_DAY_KO[s.date.weekday()],
            sleep_h=round(s.sleep_min / 60, 1),
            restless_min=s.restless_min,
        )
        for s in req.sleep
    ]


def _build_trend(
    db: Session,
    req: GenerateReportRequest,
    summary: ReportSummary,
) -> Optional[TrendData]:
    """이전 주 WeeklyData가 있으면 트렌드 계산, 없으면 None"""
    prev_data = report_repo.get_recent_weekly_data(db, req.ser_no, req.week_start, weeks=1)
    if not prev_data:
        return None

    prev = prev_data[0]
    prev_sleeps   = [s["sleep_min"]    for s in prev.sleep_json]
    prev_restless = [s["restless_min"] for s in prev.sleep_json]

    prev_avg_sleep_h   = round(sum(prev_sleeps)   / len(prev_sleeps)   / 60, 1)
    prev_avg_restless  = round(sum(prev_restless) / len(prev_restless))
    prev_cry           = prev.event_json.get("cry_count", 0)

    return TrendData(
        sleep_vs_last_week=round(summary.avg_sleep_h - prev_avg_sleep_h, 1),
        restless_vs_last_week=summary.avg_restless_min - prev_avg_restless,
        cry_vs_last_week=summary.cry_count - prev_cry,
    )


def _build_ai_context(
    db: Session,
    req: GenerateReportRequest,
    summary: ReportSummary,
) -> dict:
    """Gemini에 넘길 컨텍스트 구성 — 최대 3주치 + 일별 상세 포함"""
    ctx: dict = {
        "baby_age_months": req.baby_age_months,
        "week_label": _week_label(req.week_start),
        "this_week": {
            "avg_sleep_h":      summary.avg_sleep_h,
            "avg_restless_min": summary.avg_restless_min,
            "cry_count":        summary.cry_count,
            "leave_count":      summary.leave_count,
            "temp_avg":         req.environment.temp_avg,
            "temp_max":         req.environment.temp_max,
            "temp_min":         req.environment.temp_min,
            "db_avg":           req.environment.db_avg,
            "db_max":           req.environment.db_max,
        },
        # 일별 상세: AI가 패턴을 파악하는 데 사용
        "daily": [
            {
                "day":          _DAY_KO[s.date.weekday()],
                "sleep_h":      round(s.sleep_min / 60, 1),
                "restless_min": s.restless_min,
            }
            for s in req.sleep
        ],
    }

    prev_data = report_repo.get_recent_weekly_data(db, req.ser_no, req.week_start, weeks=2)

    if len(prev_data) >= 1:
        p = prev_data[0]
        ps = [s["sleep_min"]    for s in p.sleep_json]
        pr = [s["restless_min"] for s in p.sleep_json]
        ctx["last_week"] = {
            "avg_sleep_h":     round(sum(ps) / len(ps) / 60, 1),
            "avg_restless_min": round(sum(pr) / len(pr)),
            "cry_count":       p.event_json.get("cry_count", 0),
        }

    if len(prev_data) >= 2:
        p2 = prev_data[1]
        ps2 = [s["sleep_min"]    for s in p2.sleep_json]
        pr2 = [s["restless_min"] for s in p2.sleep_json]
        ctx["two_weeks_ago"] = {
            "avg_sleep_h":     round(sum(ps2) / len(ps2) / 60, 1),
            "avg_restless_min": round(sum(pr2) / len(pr2)),
            "cry_count":       p2.event_json.get("cry_count", 0),
        }

    return ctx


# ── Public API ─────────────────────────────────────

def generate_report(db: Session, req: GenerateReportRequest) -> GenerateReportResponse:
    """
    1. 원본 데이터 저장 (AI 컨텍스트용)
    2. 요약 / 일별 / 트렌드 계산
    3. Gemini AI 조언 생성
    4. 리포트 저장 후 리턴
    """
    # Step 1 — 원본 저장
    report_repo.save_weekly_data(
        db=db,
        ser_no=req.ser_no,
        week_start=req.week_start,
        sleep_json=[s.model_dump(mode="json") for s in req.sleep],
        env_json=req.environment.model_dump(),
        event_json=req.events.model_dump(),
    )

    # Step 2 — 집계
    summary = _build_summary(req)
    daily   = _build_daily(req)
    trend   = _build_trend(db, req, summary)

    # Step 3 — AI 조언 (최대 3주치 컨텍스트)
    ai_context = _build_ai_context(db, req, summary)
    ai_comment = generate_insight(ai_context)

    # Step 4 — 리포트 저장
    week_label  = _week_label(req.week_start)
    report_data = GenerateReportResponse(
        ser_no=req.ser_no,
        week_start=req.week_start,
        week_label=week_label,
        generated_at=datetime.now(),
        summary=summary,
        daily=daily,
        trend=trend,
        ai_comment=ai_comment,
    )

    report_repo.save_report(
        db=db,
        ser_no=req.ser_no,
        week_start=req.week_start,
        report_json=report_data.model_dump(mode="json"),
        ai_comment=ai_comment,
    )

    return report_data


def get_report_history(db: Session, ser_no: str) -> ReportHistoryResponse:
    """최근 3주치 리포트 이력 조회"""
    reports = report_repo.get_recent_reports(db, ser_no, limit=3)
    if not reports:
        raise ValueError("조회 가능한 리포트가 없습니다.")

    items = [
        ReportItem(
            week_start=r.week_start,
            week_label=_week_label(r.week_start),
            report_json=r.report_json,
        )
        for r in reports
    ]
    return ReportHistoryResponse(reports=items, total=len(items))
