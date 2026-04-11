"""
APScheduler 기반 주간 리포트 자동 생성 스케줄러
매주 월요일 오전 9시에 전체 유저의 지난 주 리포트를 생성합니다.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def _generate_all_reports():
    """지난 주(월~일) 리포트를 전체 유저 대상으로 생성"""
    from app.infrastructure.database.session import SessionLocal
    from app.domain.sleep_data.entity import User
    from app.application.report.report_service import build_report_data

    today = date.today()
    last_week_start = today - timedelta(days=today.weekday() + 7)  # 지난 주 월요일

    db = SessionLocal()
    try:
        users = db.query(User).all()
        logger.info(f"[스케줄러] 주간 리포트 생성 시작 — {len(users)}명, 기준 주: {last_week_start}")

        for user in users:
            try:
                build_report_data(db, user.user_id, last_week_start)
                logger.info(f"[스케줄러] user_id={user.user_id} ({user.baby_name}) 리포트 생성 완료")
            except Exception as e:
                logger.error(f"[스케줄러] user_id={user.user_id} 리포트 생성 실패: {e}")

    finally:
        db.close()


def start_scheduler():
    # 매주 월요일 오전 9시 실행
    _scheduler.add_job(
        _generate_all_reports,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="weekly_report",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("[스케줄러] 주간 리포트 스케줄러 시작 (매주 월요일 09:00)")
