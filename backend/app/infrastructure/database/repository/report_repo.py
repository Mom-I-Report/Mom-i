from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from app.domain.report.entity import GeneratedReport


def save_report(db: Session, user_id: int, ai_kick_comment: str,
                measured_week_start: date, report_url: str = "") -> GeneratedReport:
    report = GeneratedReport(
        user_id=user_id,
        ai_kick_comment=ai_kick_comment,
        report_url=report_url,
        measured_week_start=measured_week_start,
        is_deleted=False,
        created_at=datetime.now(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_latest_report(db: Session, user_id: int) -> Optional[GeneratedReport]:
    return (
        db.query(GeneratedReport)
        .filter(GeneratedReport.user_id == user_id, GeneratedReport.is_deleted == False)
        .order_by(GeneratedReport.created_at.desc())
        .first()
    )
