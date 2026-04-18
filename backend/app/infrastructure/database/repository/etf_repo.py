from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
import json

from app.domain.etf.entity import ETFPortfolio, ETFHolding, RebalancingHistory


# ── Portfolio ────────────────────────────────────

def get_portfolio_by_ser_no(db: Session, ser_no: str) -> Optional[ETFPortfolio]:
    return db.query(ETFPortfolio).filter(ETFPortfolio.ser_no == ser_no).first()


def upsert_portfolio(
    db: Session,
    ser_no: str,
    name: str,
    total_asset: Decimal,
    holdings: list,
) -> ETFPortfolio:
    portfolio = get_portfolio_by_ser_no(db, ser_no)
    now = datetime.now()

    if portfolio:
        portfolio.name        = name
        portfolio.total_asset = total_asset
        portfolio.updated_at  = now
        db.query(ETFHolding).filter(ETFHolding.portfolio_id == portfolio.portfolio_id).delete()
    else:
        portfolio = ETFPortfolio(
            ser_no=ser_no,
            name=name,
            total_asset=total_asset,
            created_at=now,
            updated_at=now,
        )
        db.add(portfolio)
        db.flush()  # portfolio_id 확보

    for h in holdings:
        db.add(ETFHolding(
            portfolio_id=portfolio.portfolio_id,
            ticker=h.ticker,
            name=h.name,
            target_weight=h.target_weight,
            quantity=h.quantity,
        ))

    db.commit()
    db.refresh(portfolio)
    return portfolio


def get_holdings(db: Session, portfolio_id: int) -> List[ETFHolding]:
    return db.query(ETFHolding).filter(ETFHolding.portfolio_id == portfolio_id).all()


# ── RebalancingHistory (커서 페이지네이션) ──────────

def save_rebalancing_history(
    db: Session,
    portfolio_id: int,
    ser_no: str,
    orders: list,
    total_buy: Decimal,
    total_sell: Decimal,
) -> RebalancingHistory:
    summary = json.dumps(
        [{"ticker": o["ticker"], "action": o["action"], "amount": str(o["amount"])}
         for o in orders],
        ensure_ascii=False,
    )
    record = RebalancingHistory(
        portfolio_id=portfolio_id,
        ser_no=ser_no,
        summary=summary,
        total_buy_amount=total_buy,
        total_sell_amount=total_sell,
        executed_at=datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_rebalancing_history_page(
    db: Session,
    ser_no: str,
    cursor: Optional[int],
    limit: int = 10,
) -> Tuple[List[RebalancingHistory], Optional[int]]:
    """
    커서 기반 페이지네이션.

    cursor 없음 → 최신 limit+1건 조회 (첫 페이지)
    cursor 있음 → rebalancing_id < cursor 조건으로 limit+1건 조회

    limit+1건 조회로 has_next 여부를 COUNT 없이 판단.
    실제 반환은 limit건.
    """
    query = db.query(RebalancingHistory).filter(RebalancingHistory.ser_no == ser_no)

    if cursor is not None:
        query = query.filter(RebalancingHistory.rebalancing_id < cursor)

    rows = (
        query
        .order_by(desc(RebalancingHistory.rebalancing_id))
        .limit(limit + 1)
        .all()
    )

    has_next   = len(rows) > limit
    items      = rows[:limit]
    next_cursor = items[-1].rebalancing_id if has_next else None

    return items, next_cursor
