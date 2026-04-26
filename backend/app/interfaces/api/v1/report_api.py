"""
report_api.py — 리포트 API 라우터

엔드포인트:
  POST /api/v1/reports/generate         — 주간 리포트 생성 (맘아이 서버 → API Key)
  GET  /api/v1/reports                  — 리포트 목록 카드형 (앱 → JWT)
  GET  /api/v1/reports/{report_id}      — 리포트 상세 (앱 → JWT)

인증:
  POST /generate : X-API-Key 헤더 (맘아이 서버 to 리포트 서버, 서버 to 서버)
  GET  /* :       Authorization: Bearer <JWT> (맘아이 앱 → 리포트 서버)
                  JWT payload의 ser_no와 DB의 ser_no 일치 여부를 검증해 데이터를 격리한다.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.core.security import get_current_ser_no, verify_api_key
from app.domain.report.schemas import (
    GenerateReportRequest,
    GenerateReportResponse,
    ReportListResponse,
    ReportDetailResponse,
)
from app.application.report import report_service

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateReportResponse,
    summary="주간 리포트 생성",
    dependencies=[Depends(verify_api_key)],
)
async def generate_report(
    req: GenerateReportRequest,
    db: Session = Depends(get_db),
):
    """
    맘아이 서버가 구독 유저의 주간 데이터를 push하면 AI 리포트를 생성해 리턴합니다.

    - 인증: X-API-Key 헤더 (서버 to 서버 전용)
    - 동일 주차 리포트가 이미 존재하면 캐시 반환 (Gemini 재호출 없음)
    - `sleep` 배열은 반드시 7일치 (부족하면 422 자동 반환)
    - 이전 데이터 있으면 `trend` 블록 포함, 없으면 `null`
    """
    try:
        return await report_service.generate_report(db, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "",
    response_model=ReportListResponse,
    summary="리포트 목록 조회 (카드형)",
)
async def get_reports(
    db: Session = Depends(get_db),
    ser_no: str = Depends(get_current_ser_no),
):
    """
    앱 홈 화면 및 히스토리 목록용. JWT payload의 ser_no 기준으로 본인 데이터만 반환합니다.
    최근 10건을 최신순으로 리턴합니다.
    """
    try:
        return await report_service.get_reports_list(db, ser_no)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{report_id}",
    response_model=ReportDetailResponse,
    summary="리포트 상세 조회",
)
async def get_report_detail(
    report_id: int,
    db: Session = Depends(get_db),
    ser_no: str = Depends(get_current_ser_no),
):
    """
    앱 리포트 상세 화면용. JWT의 ser_no와 리포트 소유자가 다르면 404를 반환합니다.
    summary / daily / trend / ai_comment / sleep_guide / age_kick 전체를 반환합니다.
    """
    try:
        return await report_service.get_report_detail(db, report_id, ser_no)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
