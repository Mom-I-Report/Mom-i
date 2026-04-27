"""
APScheduler 기반 스케줄러
- 매주 월요일 10:00 KST: 3주치 초과 데이터 rolling 삭제
  (리포트 생성은 맘아이 서버가 POST로 push — 이 서버에서 자동 생성하지 않음)
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def _cleanup_old_data():
    """3주치 초과 WeeklyData + GeneratedReport 물리 삭제"""
    from app.infrastructure.database.session import SessionLocal
    from app.infrastructure.database.repository.report_repo import delete_old_data

    db = SessionLocal()
    try:
        delete_old_data(db)
        logger.info("[스케줄러] 오래된 데이터 삭제 완료 (Generated_Reports 5주 초과 / Weekly_Data 12주 초과)")
    except Exception as e:
        logger.error(f"[스케줄러] 데이터 삭제 실패: {e}")
    finally:
        db.close()


def start_scheduler():
    _scheduler.add_job(
        _cleanup_old_data,
        trigger=CronTrigger(day_of_week="mon", hour=10, minute=0),
        id="cleanup_old_data",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("[스케줄러] rolling 삭제 스케줄러 시작 (매주 월요일 10:00)")
