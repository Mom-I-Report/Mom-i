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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
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
    "/emtake/generate-all",
    summary="[테스트] 전체 구독자 리포트 일괄 생성",
    dependencies=[Depends(verify_api_key)],
)
async def emtake_generate_all(
    dry_run: bool = Query(True, description="True면 리포트만 생성, 알림 발송 생략"),
    db: Session = Depends(get_db),
):
    """
    Subscriptions 테이블의 모든 활성 구독자에 대해 리포트를 생성합니다.
    dry_run=true(기본값): 리포트 생성만, 알림 미발송.
    dry_run=false: 리포트 생성 + SMS/이메일 실제 발송.
    """
    from app.application.report import report_service
    from app.domain.report.schemas import GenerateReportRequest
    from app.infrastructure.notification.sender import notify_report_ready
    from app.infrastructure.database.repository import subscription_repo

    subs = subscription_repo.get_active_subscriptions(db)
    ref_date = date.today() - timedelta(days=1)

    results = []
    for sub in subs:
        try:
            req_dict, shared_report_list = await emtake_client.build_generate_request_from_sensor(
                sub.account, sub.ser_no, ref_date, sub.ser_no
            )
            req    = GenerateReportRequest(**req_dict)
            report = await report_service.generate_report(db, req, force=True)
            if not dry_run:
                await notify_report_ready(
                    shared_report_list,
                    sub.ser_no,
                    report.week_label,
                    report.summary.avg_sleep_h,
                    report.summary.avg_restless_min,
                    report=report,
                )
            results.append({
                "ser_no":             sub.ser_no,
                "account":            sub.account,
                "status":             "ok",
                "week_label":         report.week_label,
                "avg_sleep_h":        report.summary.avg_sleep_h,
                "shared_report_list": shared_report_list,
                "notified":           not dry_run,
            })
        except Exception as e:
            results.append({
                "ser_no":  sub.ser_no,
                "account": sub.account,
                "status":  "error",
                "error":   str(e),
            })

    ok_count  = sum(1 for r in results if r["status"] == "ok")
    err_count = len(results) - ok_count
    return {"total": len(results), "ok": ok_count, "error": err_count, "results": results}


@router.post(
    "/emtake/generate",
    summary="[테스트] relay 데이터로 리포트 직접 생성",
    dependencies=[Depends(verify_api_key)],
)
async def emtake_generate(
    background_tasks: BackgroundTasks,
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
        report = await report_service.generate_report(db, req, force=True)
        from app.infrastructure.notification.sender import notify_report_ready
        background_tasks.add_task(
            notify_report_ready,
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
            "shared_report_list": shared_report_list,
            "report":             report.model_dump(mode="json"),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/reports/pdf",
    summary="최신 리포트 PDF 다운로드",
    dependencies=[Depends(verify_api_key)],
)
async def download_report_pdf(
    ser_no: str = Query(..., example="TEST1"),
    version: str = Query("mobile", description="mobile 또는 pc"),
    db: Session = Depends(get_db),
):
    from app.infrastructure.database.repository.report_repo import get_reports_list
    from app.domain.report.schemas import GenerateReportResponse
    from app.core.config import settings

    reports = get_reports_list(db, ser_no, limit=1)
    if not reports:
        raise HTTPException(status_code=404, detail="리포트가 없습니다.")

    latest = reports[0]
    report = GenerateReportResponse.model_validate(latest.report_json)

    if settings.FRONTEND_URL:
        pdf_bytes = await _capture_pdf_from_frontend(report, version, settings.FRONTEND_URL)
    else:
        from app.infrastructure.notification.pdf_generator import generate_report_pdfs
        mobile_pdf, pc_pdf = await generate_report_pdfs(report)
        pdf_bytes = mobile_pdf if version == "mobile" else pc_pdf

    filename = f"momi_{report.week_start}_{version}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


async def _capture_pdf_from_frontend(report, version: str, frontend_url: str) -> bytes:
    import base64, json
    from playwright.async_api import async_playwright

    encoded = base64.b64encode(json.dumps(report.model_dump(mode="json")).encode()).decode()
    url = f"{frontend_url}/demo.html?report={encoded}&mode={version}"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        width = 390 if version == "mobile" else 860
        await page.set_viewport_size({"width": width, "height": 1200})
        await page.goto(url, wait_until="networkidle", timeout=30000)
        # React 렌더링 + 차트 등 완전히 그려질 때까지 대기
        await page.wait_for_timeout(4000)
        # 전체 페이지 높이로 뷰포트 조정
        height = await page.evaluate("document.body.scrollHeight")
        await page.set_viewport_size({"width": width, "height": max(height, 1200)})
        await page.wait_for_timeout(500)
        pdf = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        await browser.close()
    return pdf
