from sqlalchemy.orm import Session
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from datetime import datetime

from app.infrastructure.database.repository import etf_repo
from app.infrastructure.market.price_client import price_client
from app.domain.etf.schemas import (
    CreatePortfolioRequest,
    RebalanceResponse,
    OrderItem,
    HistoryPageResponse,
    HistoryItem,
)

_DRIFT_THRESHOLD = 0.05     # 5% 이상 괴리 시 BUY/SELL, 미만이면 HOLD


def create_or_update_portfolio(db: Session, ser_no: str, req: CreatePortfolioRequest):
    """포트폴리오 생성 또는 전체 교체"""
    return etf_repo.upsert_portfolio(db, ser_no, req.name, req.total_asset, req.holdings)


def calculate_rebalancing(
    db: Session,
    ser_no: str,
    dry_run: bool = True,
) -> RebalanceResponse:
    """
    핵심 리밸런싱 알고리즘:
    1. 포트폴리오 + 보유 ETF 조회
    2. 시장가 fetch
    3. 현재 보유 비중 계산
    4. 목표 비중과 괴리(drift) 계산
    5. 매수/매도 주문 금액 산출
    6. dry_run=False 이면 이력 DB 저장
    """
    portfolio = etf_repo.get_portfolio_by_ser_no(db, ser_no)
    if not portfolio:
        raise ValueError(f"포트폴리오가 없습니다. 먼저 생성하세요. (ser_no={ser_no})")

    holdings = etf_repo.get_holdings(db, portfolio.portfolio_id)
    if not holdings:
        raise ValueError("보유 ETF가 없습니다.")

    tickers = [h.ticker for h in holdings]
    prices  = price_client.fetch_prices(tickers)

    total_asset = Decimal(str(portfolio.total_asset))

    # 현재 보유 평가액
    holding_values: dict[str, Decimal] = {
        h.ticker: Decimal(str(prices.get(h.ticker, 0))) * Decimal(str(h.quantity))
        for h in holdings
    }
    current_total = sum(holding_values.values()) or total_asset

    orders: List[OrderItem] = []
    total_buy  = Decimal("0")
    total_sell = Decimal("0")

    for h in holdings:
        price          = Decimal(str(prices.get(h.ticker, 0)))
        current_value  = holding_values[h.ticker]
        current_weight = float(current_value / current_total) if current_total else 0.0
        target_weight  = h.target_weight
        drift          = round(current_weight - target_weight, 4)

        target_value = total_asset * Decimal(str(target_weight))
        delta_amount = target_value - current_value     # 양수: 매수, 음수: 매도

        if abs(drift) < _DRIFT_THRESHOLD:
            action       = "HOLD"
            delta_amount = Decimal("0")
        elif delta_amount > 0:
            action = "BUY"
            total_buy += delta_amount
        else:
            action = "SELL"
            total_sell += abs(delta_amount)

        qty_change = float(delta_amount / price) if price else 0.0

        orders.append(OrderItem(
            ticker=h.ticker,
            name=h.name or h.ticker,
            action=action,
            current_weight=round(current_weight, 4),
            target_weight=round(target_weight, 4),
            drift=drift,
            amount=delta_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            quantity_change=round(qty_change, 4),
        ))

    if not dry_run:
        etf_repo.save_rebalancing_history(
            db=db,
            portfolio_id=portfolio.portfolio_id,
            ser_no=ser_no,
            orders=[o.model_dump() for o in orders],
            total_buy=total_buy,
            total_sell=total_sell,
        )

    return RebalanceResponse(
        portfolio_id=portfolio.portfolio_id,
        total_asset=total_asset,
        orders=orders,
        total_buy_amount=total_buy.quantize(Decimal("0.01")),
        total_sell_amount=total_sell.quantize(Decimal("0.01")),
        executed_at=datetime.now(),
        dry_run=dry_run,
    )


def get_history_page(
    db: Session,
    ser_no: str,
    cursor: Optional[int],
    limit: int,
) -> HistoryPageResponse:
    """커서 기반 페이지네이션으로 리밸런싱 이력 반환"""
    if limit < 1 or limit > 100:
        raise ValueError("limit은 1 이상 100 이하여야 합니다")

    rows, next_cursor = etf_repo.get_rebalancing_history_page(db, ser_no, cursor, limit)

    items = [
        HistoryItem(
            rebalancing_id=r.rebalancing_id,
            total_buy_amount=r.total_buy_amount,
            total_sell_amount=r.total_sell_amount,
            executed_at=r.executed_at,
            summary=r.summary or "",
        )
        for r in rows
    ]

    return HistoryPageResponse(
        items=items,
        next_cursor=next_cursor,
        has_next=next_cursor is not None,
    )
