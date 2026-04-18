from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, timedelta
from typing import List, Optional

from app.domain.report.entity import WeeklyData, GeneratedReport


# ── Weekly_Data ─────────────────────────────────────

def save_weekly_data(
    db: Session,
    ser_no: str,
    week_start: date,
    sleep_json: list,
    env_json: dict,
    event_json: dict,
) -> WeeklyData:
    """주간 원본 데이터 저장 (upsert) — AI 컨텍스트 3주치 보관용"""
    existing = db.query(WeeklyData).filter(
        and_(WeeklyData.ser_no == ser_no, WeeklyData.week_start == week_start)
    ).first()

    if existing:
        existing.sleep_json = sleep_json
        existing.env_json   = env_json
        existing.event_json = event_json
    else:
        existing = WeeklyData(
            ser_no=ser_no,
            week_start=week_start,
            sleep_json=sleep_json,
            env_json=env_json,
            event_json=event_json,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def get_recent_weekly_data(
    db: Session,
    ser_no: str,
    week_start: date,
    weeks: int = 2,
) -> List[WeeklyData]:
    """이전 N주치 WeeklyData 조회 — AI 트렌드 컨텍스트용 (이번 주 제외)"""
    cutoff = week_start - timedelta(weeks=weeks)
    return (
        db.query(WeeklyData)
        .filter(
            and_(
                WeeklyData.ser_no == ser_no,
                WeeklyData.week_start >= cutoff,
                WeeklyData.week_start < week_start,
            )
        )
        .order_by(WeeklyData.week_start.desc())
        .all()
    )


# ── Generated_Reports ───────────────────────────────

def save_report(
    db: Session,
    ser_no: str,
    week_start: date,
    report_json: dict,
    ai_comment: str,
) -> GeneratedReport:
    """리포트 저장 (upsert) — 동일 주차 재전송 시 덮어쓰기"""
    existing = db.query(GeneratedReport).filter(
        and_(GeneratedReport.ser_no == ser_no, GeneratedReport.week_start == week_start)
    ).first()

    if existing:
        existing.report_json = report_json
        existing.ai_comment  = ai_comment
    else:
        existing = GeneratedReport(
            ser_no=ser_no,
            week_start=week_start,
            report_json=report_json,
            ai_comment=ai_comment,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def get_recent_reports(
    db: Session,
    ser_no: str,
    limit: int = 3,
) -> List[GeneratedReport]:
    """최근 3주치 리포트 조회 — 앱 재열람용"""
    cutoff = date.today() - timedelta(weeks=3)
    return (
        db.query(GeneratedReport)
        .filter(
            and_(
                GeneratedReport.ser_no == ser_no,
                GeneratedReport.week_start >= cutoff,
            )
        )
        .order_by(GeneratedReport.week_start.desc())
        .limit(limit)
        .all()
    )


# ── Rolling 삭제 ────────────────────────────────────

def delete_old_data(db: Session) -> None:
    """3주치 초과 데이터 물리 삭제 — 매주 스케줄러에서 호출"""
    cutoff = date.today() - timedelta(weeks=3)
    db.query(WeeklyData).filter(WeeklyData.week_start < cutoff).delete()
    db.query(GeneratedReport).filter(GeneratedReport.week_start < cutoff).delete()
    db.commit()
