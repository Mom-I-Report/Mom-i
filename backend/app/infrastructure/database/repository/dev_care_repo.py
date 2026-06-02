"""
dev_care_repo.py — Developmental_Care 테이블 조회
"""
from sqlalchemy.orm import Session
from typing import Optional

from app.domain.report.entity import DevelopmentalCare


def get_by_age_weeks(db: Session, age_weeks: int) -> Optional[DevelopmentalCare]:
    return (
        db.query(DevelopmentalCare)
        .filter(DevelopmentalCare.age_weeks == age_weeks)
        .first()
    )


def get_by_age_months(db: Session, age_months: int) -> Optional[DevelopmentalCare]:
    """월령으로 조회. weekly 타입은 해당 월의 첫 주차, monthly 타입은 정확히 일치."""
    return (
        db.query(DevelopmentalCare)
        .filter(DevelopmentalCare.age_months == age_months)
        .order_by(DevelopmentalCare.age_weeks.asc())
        .first()
    )
