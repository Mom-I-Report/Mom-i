"""
share_repo.py — Share_Targets DB 접근 레이어
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional

from app.domain.report.entity import ShareTarget

MAX_TARGETS_PER_DEVICE = 5


def get_targets(db: Session, ser_no: str) -> List[ShareTarget]:
    return (
        db.query(ShareTarget)
        .filter(ShareTarget.ser_no == ser_no)
        .order_by(ShareTarget.created_at.asc())
        .all()
    )


def count_targets(db: Session, ser_no: str) -> int:
    return db.query(ShareTarget).filter(ShareTarget.ser_no == ser_no).count()


def get_target_by_id(db: Session, target_id: int) -> Optional[ShareTarget]:
    return db.query(ShareTarget).filter(ShareTarget.id == target_id).first()


def create_target(
    db: Session,
    ser_no: str,
    name: str,
    contact: str,
    type_: str,
) -> ShareTarget:
    target = ShareTarget(ser_no=ser_no, name=name, contact=contact, type=type_)
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def delete_target(db: Session, target: ShareTarget) -> None:
    db.delete(target)
    db.commit()
