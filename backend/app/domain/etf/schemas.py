from pydantic import BaseModel, field_validator
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


# ── 요청 스키마 ──────────────────────────────────

class ETFHoldingIn(BaseModel):
    ticker: str
    name: str
    target_weight: float        # 0.0 ~ 1.0
    quantity: float = 0.0

    @field_validator("target_weight")
    @classmethod
    def weight_range(cls, v: float) -> float:
        if not (0.0 < v <= 1.0):
            raise ValueError("target_weight는 0 초과 1 이하여야 합니다")
        return v


class CreatePortfolioRequest(BaseModel):
    name: str
    total_asset: Decimal                # 총 자산 (원화)
    holdings: List[ETFHoldingIn]

    @field_validator("holdings")
    @classmethod
    def weights_sum_to_one(cls, holdings: List[ETFHoldingIn]) -> List[ETFHoldingIn]:
        total = sum(h.target_weight for h in holdings)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"목표 비중 합산이 1.0이어야 합니다 (현재: {total:.4f})")
        return holdings


class RebalanceRequest(BaseModel):
    """리밸런싱 실행 요청"""
    dry_run: bool = True    # True: 계획만 반환 / False: 이력 DB 저장


# ── 응답 스키마 ──────────────────────────────────

class OrderItem(BaseModel):
    ticker: str
    name: str
    action: str             # "BUY" | "SELL" | "HOLD"
    current_weight: float   # 현재 비중
    target_weight: float    # 목표 비중
    drift: float            # 괴리율 (current - target)
    amount: Decimal         # 매수/매도 금액 (원화)
    quantity_change: float  # 매수/매도 수량


class RebalanceResponse(BaseModel):
    portfolio_id: int
    total_asset: Decimal
    orders: List[OrderItem]
    total_buy_amount: Decimal
    total_sell_amount: Decimal
    executed_at: datetime
    dry_run: bool


class HistoryItem(BaseModel):
    rebalancing_id: int     # 커서 값
    total_buy_amount: Decimal
    total_sell_amount: Decimal
    executed_at: datetime
    summary: str            # 주문 플랜 JSON 요약


class HistoryPageResponse(BaseModel):
    """커서 기반 페이지 응답"""
    items: List[HistoryItem]
    next_cursor: Optional[int]  # None이면 마지막 페이지
    has_next: bool
