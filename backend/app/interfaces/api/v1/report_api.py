from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.domain.report.schemas import (
    GenerateReportRequest,
    GenerateReportResponse,
    ReportHistoryResponse,
)
from app.application.report import report_service

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateReportResponse,
    summary="주간 리포트 생성",
)
def generate_report(
    req: GenerateReportRequest,
    db: Session = Depends(get_db),
):
    """
    맘아이 서버가 구독 유저의 주간 데이터를 push하면 AI 리포트를 생성해 리턴합니다.

    - `sleep` 배열은 반드시 7일치 (validator로 강제)
    - 개인정보 불포함 — `ser_no` + `baby_age_months`만 사용
    - 3주치 데이터가 있으면 `trend` 블록 포함, 없으면 `null`
    """
    try:
        return report_service.generate_report(db, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history/{ser_no}",
    response_model=ReportHistoryResponse,
    summary="리포트 이력 조회 (최근 3주)",
)
def get_history(
    ser_no: str,
    db: Session = Depends(get_db),
):
    """
    사용자가 앱에서 이전 리포트를 재열람할 때 호출합니다.
    최근 3주치(최대 3개)를 최신순으로 리턴합니다.
    """
    try:
        return report_service.get_report_history(db, ser_no)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
