"""
admin_api.py — 관리자 대시보드 API

엔드포인트:
  GET /admin/stats                       — 서버 운영 통계 조회
  GET /admin/emtake/ping                 — EMTAKE API 연결 확인 (원시 응답)
  GET /admin/emtake/sleep                — EMTAKE SleepData 파싱 결과 확인

인증:
  X-API-Key 헤더 (ADMIN_API_KEY) — 내부 관리용 전용
  앱 사용자는 접근 불가.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.core.security import verify_api_key
from app.infrastructure.database.repository import report_repo
from app.infrastructure.emtake import client as emtake_client

router = APIRouter()


@router.get(
    "/devices",
    summary="기기 목록 조회",
    dependencies=[Depends(verify_api_key)],
)
def get_devices(db: Session = Depends(get_db)):
    """
    리포트가 존재하는 모든 기기(ser_no) 목록과 통계를 반환합니다.

    - ser_no         : 기기 시리얼 번호
    - subscribed_at  : 최초 리포트 생성일 (구독 시작일로 간주)
    - last_report_at : 가장 최근 리포트 생성일
    - report_count   : 총 리포트 수
    """
    return report_repo.get_all_devices(db)


@router.get(
    "/devices/{ser_no}/reports",
    summary="기기별 최근 3주치 리포트 조회",
    dependencies=[Depends(verify_api_key)],
)
def get_device_reports(ser_no: str, db: Session = Depends(get_db)):
    """
    특정 기기의 최근 3주치 리포트 전체 JSON을 반환합니다.

    - report_id   : 리포트 PK
    - week_start  : 주 시작일
    - created_at  : 리포트 생성 시각
    - report_json : 전체 리포트 데이터 (summary, breath, body_temp, daily, trend, ai_comment 등)
    """
    return report_repo.get_device_reports(db, ser_no, limit=3)


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


@router.get(
    "/emtake/ping",
    summary="EMTAKE API 원시 응답 확인",
    dependencies=[Depends(verify_api_key)],
)
async def emtake_ping(
    account: str = Query(..., description="맘아이 계정 이메일", example="test1@test1.com"),
    uid: str     = Query(..., description="기기 시리얼 번호",   example="SERIAL"),
    cmd: str     = Query("SleepData", description="EMTAKE CMD"),
):
    """
    EMTAKE relay API를 직접 호출해 원시 응답을 반환합니다.

    - 연결 상태 및 응답 포맷 확인용
    - 파싱 없이 EMTAKE가 반환하는 raw JSON 그대로 반환
    - 목요일(2026-04-30) 추가 CMD 응답 포맷 확인에 사용
    """
    try:
        # pylint: disable=protected-access
        raw = await emtake_client._fetch_raw(account, uid, cmd)
        return {"cmd": cmd, "account": account, "uid": uid, "raw": raw}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"EMTAKE API 호출 실패: {e}")


@router.get(
    "/emtake/sleep",
    summary="EMTAKE SleepData 파싱 결과 확인",
    dependencies=[Depends(verify_api_key)],
)
async def emtake_sleep(
    account: str = Query(..., description="맘아이 계정 이메일", example="test1@test1.com"),
    uid: str     = Query(..., description="기기 시리얼 번호",   example="SERIAL"),
):
    """
    EMTAKE SleepData CMD를 호출하고 분·시간 단위로 파싱한 결과를 반환합니다.

    반환 필드:
    - day_sleep_min / day_restless_min     : 오늘 수면·뒤척임 (분)
    - week_sleep_min / week_restless_min   : 주간 평균 수면·뒤척임 (분)
    - month_sleep_h / month_restless_h     : 월간 평균 수면·뒤척임 (시간)

    현재 한계:
      날짜별 7일치 상세 데이터 없음 → 목요일 추가 예정 CMD로 보완 필요.
      GenerateReportRequest의 sleep[7] 구성에는 추가 데이터가 필요합니다.
    """
    try:
        parsed = await emtake_client.fetch_sleep_data(account, uid)
        return {"account": account, "uid": uid, "parsed": parsed}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"EMTAKE SleepData 호출 실패: {e}")


@router.post(
    "/emtake/generate",
    summary="[테스트] relay 데이터로 리포트 직접 생성",
    dependencies=[Depends(verify_api_key)],
)
async def emtake_generate(
    account: str = Query(..., example="test1@test.com"),
    uid:     str = Query(..., example="TEST1"),
    ser_no:  str = Query(..., example="TEST-SER-001"),
    db: Session = Depends(get_db),
):
    """
    EMTAKE relay에서 7일치 데이터를 수집해 리포트를 생성합니다.
    스케줄러 흐름 전체를 수동으로 트리거하는 테스트용 엔드포인트.
    ref_date = 어제 (오늘 기준 -1일).
    """
    from app.application.report import report_service
    from app.domain.report.schemas import GenerateReportRequest

    ref_date = date.today() - timedelta(days=1)
    try:
        req_dict, shared_report_list = await emtake_client.build_generate_request_from_sensor(
            account, uid, ref_date, ser_no
        )
        req    = GenerateReportRequest(**req_dict)
        report = await report_service.generate_report(db, req)
        from app.infrastructure.notification.sender import notify_report_ready
        await notify_report_ready(
            shared_report_list,
            ser_no,
            report.week_label,
            report.summary.avg_sleep_h,
            report.summary.avg_restless_min,
            report=report,
        )
        return {
            "status":             "ok",
            "week_start":         str(report.week_start),
            "week_label":         report.week_label,
            "avg_sleep_h":        report.summary.avg_sleep_h,
            "avg_restless_min":   report.summary.avg_restless_min,
            "ai_comment_count":   len(report.ai_comment),
            "sleep_guide":        report.sleep_guide.method_name if report.sleep_guide else None,
            "shared_report_list": shared_report_list,
            "notifications_sent": len([c for c in shared_report_list if "@" in c]),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
