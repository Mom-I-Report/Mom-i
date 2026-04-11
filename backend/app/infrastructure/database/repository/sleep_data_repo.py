from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from typing import List, Optional

from app.domain.sleep_data.entity import User, DailySleepLog, EnvironmentLog, EventLog


def get_user_by_ser_no(db: Session, ser_no: str) -> Optional[User]:
    return db.query(User).filter(User.ser_no == ser_no).first()


def save_sleep_log(db: Session, user_id: int, day_gs: str, day_pr: str, measured_date: date):
    log = DailySleepLog(
        user_id=user_id,
        day_gs=day_gs,
        day_pr=day_pr,
        measured_date=measured_date,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def save_environment_log(db: Session, user_id: int, temp_avg: float, temp_max: float,
                         temp_min: float, db_max: int, measured_date: date):
    log = EnvironmentLog(
        user_id=user_id,
        temp_avg=temp_avg,
        temp_max=temp_max,
        temp_min=temp_min,
        db_max=db_max,
        measured_date=measured_date,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def save_event_log(db: Session, user_id: int, event_type: str, event_time):
    log = EventLog(user_id=user_id, event_type=event_type, event_time=event_time)
    db.add(log)
    db.commit()
    return log


def get_weekly_sleep_logs(db: Session, user_id: int, week_start: date) -> List[DailySleepLog]:
    week_end = week_start + timedelta(days=6)
    return (
        db.query(DailySleepLog)
        .filter(
            DailySleepLog.user_id == user_id,
            DailySleepLog.measured_date >= week_start,
            DailySleepLog.measured_date <= week_end,
        )
        .order_by(DailySleepLog.measured_date)
        .all()
    )


def get_weekly_environment_logs(db: Session, user_id: int, week_start: date) -> List[EnvironmentLog]:
    week_end = week_start + timedelta(days=6)
    return (
        db.query(EnvironmentLog)
        .filter(
            EnvironmentLog.user_id == user_id,
            EnvironmentLog.measured_date >= week_start,
            EnvironmentLog.measured_date <= week_end,
        )
        .all()
    )


def get_weekly_event_logs(db: Session, user_id: int, week_start: date) -> List[EventLog]:
    week_end = week_start + timedelta(days=6)
    from datetime import datetime
    return (
        db.query(EventLog)
        .filter(
            EventLog.user_id == user_id,
            EventLog.event_time >= datetime.combine(week_start, datetime.min.time()),
            EventLog.event_time <= datetime.combine(week_end, datetime.max.time()),
        )
        .all()
    )
