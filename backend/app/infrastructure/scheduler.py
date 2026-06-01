"""
scheduler.py — APScheduler 기반 정기 작업

작업 목록:
  1. 매주 월요일 09:00 KST — 구독자 전체 주간 리포트 자동 생성 + 알림 발송
  2. 매주 월요일 10:00 KST — rolling 삭제 (Generated_Reports 5주 / Weekly_Data 12주)
"""
import asyncio
import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")


# ── 작업 1: 주간 리포트 자동 생성 ────────────────────────────────────────────

def _generate_weekly_reports():
    """
    활성 구독자 전체를 순회해 직전 주(월~일) 리포트를 자동 생성하고 알림을 발송한다.

    ref_date  = 어제 (일요일) — EMTAKE relay의 마지막 날 기준
    week_start = ref_date - 6일 (월요일)
    """
    from app.infrastructure.database.session import SessionLocal
    from app.infrastructure.database.repository.subscription_repo import get_active_subscriptions
    from app.infrastructure.emtake.client import build_generate_request_from_sensor
    from app.infrastructure.notification.sender import notify_report_ready
    from app.application.report import report_service
    from app.domain.report.schemas import GenerateReportRequest

    ref_date = date.today() - timedelta(days=1)  # 어제 (일요일)
    db = SessionLocal()

    try:
        subscriptions = get_active_subscriptions(db)
        logger.info("[스케줄러] 주간 리포트 생성 시작 — 구독자 %d명 / 기준일 %s", len(subscriptions), ref_date)

        for sub in subscriptions:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                req_dict, shared_report_list = loop.run_until_complete(
                    build_generate_request_from_sensor(sub.account, sub.ser_no, ref_date, sub.ser_no, sub.user_type)
                )
                req    = GenerateReportRequest(**req_dict)
                report = loop.run_until_complete(report_service.generate_report(db, req))

                loop.run_until_complete(
                    notify_report_ready(
                        shared_report_list,
                        sub.ser_no,
                        report.week_label,
                        report.summary.avg_sleep_h,
                        report.summary.avg_restless_min,
                        report=report,
                    )
                )
                logger.info("[스케줄러] 완료 ser_no=%s week=%s", sub.ser_no, report.week_start)

            except Exception as e:
                logger.error("[스케줄러] 실패 ser_no=%s: %s", sub.ser_no, e)
            finally:
                loop.close()

    except Exception as e:
        logger.error("[스케줄러] 전체 실패: %s", e)
    finally:
        db.close()


# ── 작업 2: rolling 삭제 ─────────────────────────────────────────────────────

def _cleanup_old_data():
    """보존 기간 초과 데이터 물리 삭제 (Generated_Reports 5주 / Weekly_Data 12주)"""
    from app.infrastructure.database.session import SessionLocal
    from app.infrastructure.database.repository.report_repo import delete_old_data

    db = SessionLocal()
    try:
        delete_old_data(db)
        logger.info("[스케줄러] 오래된 데이터 삭제 완료")
    except Exception as e:
        logger.error("[스케줄러] 데이터 삭제 실패: %s", e)
    finally:
        db.close()


# ── 스케줄러 시작 ─────────────────────────────────────────────────────────────

def start_scheduler():
    _scheduler.add_job(
        _generate_weekly_reports,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="generate_weekly_reports",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _cleanup_old_data,
        trigger=CronTrigger(day_of_week="mon", hour=10, minute=0),
        id="cleanup_old_data",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("[스케줄러] 시작 — 리포트 생성 매주 월 09:00 / 삭제 매주 월 10:00")
