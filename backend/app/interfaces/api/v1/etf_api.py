from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.infrastructure.database.session import get_db
from app.domain.etf.schemas import (
    CreatePortfolioRequest,
    RebalanceResponse,
    RebalanceRequest,
    HistoryPageResponse,
)
from app.application.etf import rebalance_service

router = APIRouter()


@router.post("/portfolio/{ser_no}", summary="포트폴리오 생성/갱신")
def create_portfolio(
    ser_no: str,
    req: CreatePortfolioRequest,
    db: Session = Depends(get_db),
):
    """
    ETF 포트폴리오를 생성하거나 전체 교체합니다.
    - `holdings`의 `target_weight` 합산이 반드시 1.0이어야 합니다.
    - `ser_no`: 카메라 시리얼 번호 (Users 테이블 없음, ser_no로 식별)
    """
    try:
        portfolio = rebalance_service.create_or_update_portfolio(db, ser_no, req)
        return {"status": "success", "portfolio_id": portfolio.portfolio_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rebalance/{ser_no}", response_model=RebalanceResponse, summary="리밸런싱 실행")
def run_rebalance(
    ser_no: str,
    req: RebalanceRequest,
    db: Session = Depends(get_db),
):
    """
    현재 시장가를 조회하여 리밸런싱 주문 플랜을 계산합니다.

    - `dry_run=true` (기본): 계획만 반환, DB 저장 없음
    - `dry_run=false`: 이력 저장 후 반환
    - 괴리율 5% 미만 ETF는 `HOLD` 처리
    """
    try:
        return rebalance_service.calculate_rebalancing(db, ser_no, req.dry_run)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/rebalance/history/{ser_no}",
    response_model=HistoryPageResponse,
    summary="리밸런싱 이력 조회 (커서 페이지네이션)",
)
def get_history(
    ser_no: str,
    cursor: Optional[int] = Query(
        default=None,
        description="마지막으로 받은 rebalancing_id. 없으면 첫 페이지.",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="페이지당 항목 수 (1~100)",
    ),
    db: Session = Depends(get_db),
):
    """
    커서 기반 페이지네이션으로 리밸런싱 이력을 최신순으로 반환합니다.

    **클라이언트 사용법:**
    1. 첫 요청: `GET /api/v1/etf/rebalance/history/MT-00123?limit=10`
    2. 이후 요청: 응답의 `next_cursor`를 `cursor`로 전달
    3. `has_next=false`이면 마지막 페이지
    """
    try:
        return rebalance_service.get_history_page(db, ser_no, cursor, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
