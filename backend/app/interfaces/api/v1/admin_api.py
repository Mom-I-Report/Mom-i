"""
admin_api.py — 관리자 대시보드 API

엔드포인트:
  GET /admin/stats — 서버 운영 통계 조회

인증:
  X-API-Key 헤더 (ADMIN_API_KEY) — 내부 관리용 전용
  앱 사용자는 접근 불가.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.core.security import verify_api_key
from app.infrastructure.database.repository import report_repo

router = APIRouter()


@router.get(
    "/stats",
    summary="관리자 대시보드 통계",
    dependencies=[Depends(verify_api_key)],
)
def get_admin_stats(db: Session = Depends(get_db)):
    """
    관리자 대시보드용 운영 통계를 반환합니다.

    - 인증: X-API-Key 헤더 필수
    - total_reports   : 전체 리포트 생성 건수
    - active_devices  : 리포트가 있는 고유 기기(ser_no) 수
    - today_reports   : 오늘 생성 건수
    - week_reports    : 이번 주 생성 건수
    - last_generated_at : 가장 최근 생성 시각
    - recent_reports  : 최근 10건 요약 (report_id, ser_no, week_start, created_at)
    """
    return report_repo.get_admin_stats(db)
