"""
subscription_repo.py — Subscriptions DB 접근 레이어
"""
from sqlalchemy.orm import Session
from typing import List, Optional

from app.domain.report.entity import Subscription


def get_active_subscriptions(db: Session) -> List[Subscription]:
    return db.query(Subscription).filter(Subscription.is_active == True).all()


def get_by_ser_no(db: Session, ser_no: str) -> Optional[Subscription]:
    return db.query(Subscription).filter(Subscription.ser_no == ser_no).first()


def create_subscription(
    db: Session,
    ser_no: str,
    account: str,
    user_type: str = "LLMREPORT",
) -> Subscription:
    existing = get_by_ser_no(db, ser_no)
    if existing:
        existing.account   = account
        existing.user_type = user_type
        existing.is_active = True
    else:
        existing = Subscription(ser_no=ser_no, account=account, user_type=user_type)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def deactivate_subscription(db: Session, ser_no: str) -> bool:
    sub = get_by_ser_no(db, ser_no)
    if not sub:
        return False
    sub.is_active = False
    db.commit()
    return True
