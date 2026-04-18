"""
더미 데이터 삽입 스크립트
backend 폴더에서 실행: python seed.py
"""
from datetime import date, datetime, timedelta
from app.infrastructure.database.session import SessionLocal, create_tables
from app.domain.sleep_data.entity import User, DailySleepLog, EnvironmentLog, EventLog

WEEK_START = date(2025, 4, 7)  # 월요일

SLEEP_DATA = [
    ("9h30m", "22m"),
    ("8h45m", "20m"),
    ("9h15m", "14m"),
    ("9h40m", "12m"),
    ("8h55m", "19m"),
    ("9h05m", "21m"),
    ("9h50m", "16m"),
]

ENV_DATA = [
    (23.1, 24.2, 22.0, 58),
    (22.8, 23.9, 21.5, 61),
    (23.4, 24.5, 22.3, 55),
    (23.0, 24.1, 21.8, 62),
    (22.9, 24.0, 21.6, 59),
    (23.2, 24.3, 22.1, 57),
    (23.5, 24.6, 22.4, 60),
]

EVENTS = [
    ("Crying", datetime(2025, 4,  7, 2, 15)),
    ("Crying", datetime(2025, 4,  9, 3, 42)),
    ("Leave",  datetime(2025, 4, 10, 1, 30)),
    ("Crying", datetime(2025, 4, 11, 4,  5)),
]


def seed():
    create_tables()
    db = SessionLocal()

    try:
        # 기존 유저 중복 방지
        existing = db.query(User).filter(User.ser_no == "MT-00123").first()
        if existing:
            print("이미 더미 데이터가 존재합니다.")
            return

        # ── 유저 등록 ──
        user = User(
            email="parent@example.com",
            baby_name="민준",
            baby_birth=date(2024, 8, 15),
            baby_gender="M",
            ser_no="MT-00123",
            created_at=datetime.now(),
        )
        db.add(user)
        db.flush()  # user_id 확보

        # ── 7일치 수면 로그 ──
        for i, (gs, pr) in enumerate(SLEEP_DATA):
            db.add(DailySleepLog(
                user_id=user.user_id,
                day_gs=gs,
                day_pr=pr,
                measured_date=WEEK_START + timedelta(days=i),
            ))

        # ── 7일치 환경 로그 ──
        for i, (avg, mx, mn, dbm) in enumerate(ENV_DATA):
            db.add(EnvironmentLog(
                user_id=user.user_id,
                temp_avg=avg,
                temp_max=mx,
                temp_min=mn,
                db_max=dbm,
                measured_date=WEEK_START + timedelta(days=i),
            ))

        # ── 이벤트 로그 ──
        for etype, etime in EVENTS:
            db.add(EventLog(
                user_id=user.user_id,
                event_type=etype,
                event_time=etime,
            ))

        db.commit()
        print(f"더미 데이터 삽입 완료! user_id={user.user_id}")
        print(f"리포트 확인: http://localhost:8000/api/v1/report/{user.user_id}?week_start=2025-04-07")

    except Exception as e:
        db.rollback()
        print(f"오류: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
