# ETF 리밸런싱 기능 구현 계획

> 기준 브랜치: `feat/noh`  
> 작성일: 2026-04-15  
> 기존 아키텍처: FastAPI + SQLAlchemy + Clean Architecture (4레이어)  
> **스펙 기준:** `report_server_spec.md` — 이 서버는 `Users` 테이블 없음, `ser_no`로 식별

---

## 1. 목표

맘아이 백엔드에 **ETF 포트폴리오 리밸런싱** 기능을 추가한다.

- 사용자별 ETF 목표 비중 관리
- 현재 시장가 조회 후 실제 보유 비중과 목표 비중 간 괴리 계산
- 리밸런싱 매수/매도 주문 플랜 생성
- 리밸런싱 실행 이력 저장 및 **커서 기반 페이지네이션** 조회

---

## 2. 왜 커서 기반 페이지네이션인가

### 오프셋 페이징의 문제

```
# 오프셋 방식: LIMIT 10 OFFSET 20
# → 새 리밸런싱이 생기면 페이지 경계가 밀려 항목이 중복되거나 누락됨
# → 전체 COUNT 쿼리가 필요해 대용량에서 느림
```

### 커서(입력값) 기반 페이징의 장점

```
# 커서 방식: WHERE rebalancing_id < :cursor ORDER BY rebalancing_id DESC LIMIT 10
# → 커서(마지막으로 본 ID)를 기준으로 다음 페이지를 정확하게 잘라냄
# → 실시간으로 데이터가 추가돼도 누락/중복 없음
# → COUNT 불필요, 인덱스만으로 O(log n) 탐색
```

**커서 설계 원칙:**
- 커서 = 클라이언트가 마지막으로 받은 항목의 `rebalancing_id`
- 첫 요청: `cursor` 파라미터 없음 → 최신 N건 반환
- 이후 요청: 응답에서 받은 `next_cursor`를 `cursor`로 전달
- `next_cursor == null` → 마지막 페이지

---

## 3. 추가할 파일 목록

기존 clean architecture 레이어 구조를 그대로 따른다.

```
backend/app/
├── domain/etf/
│   ├── __init__.py
│   ├── entity.py          ← ORM 모델 (ETFPortfolio, ETFHolding, RebalancingHistory)
│   └── schemas.py         ← Pydantic 요청/응답 스키마
├── application/etf/
│   ├── __init__.py
│   └── rebalance_service.py   ← 리밸런싱 핵심 비즈니스 로직
├── infrastructure/
│   ├── database/repository/
│   │   └── etf_repo.py    ← DB 접근 (커서 페이지네이션 포함)
│   └── market/
│       ├── __init__.py
│       └── price_client.py    ← 시장가 조회 외부 API 클라이언트
└── interfaces/api/v1/
    └── etf_api.py         ← FastAPI 라우터
```

수정 파일:
- `backend/app/main.py` — 새 라우터 등록
- `backend/app/core/config.py` — MARKET_API_KEY 추가
- `backend/requirements.txt` — httpx (이미 있음, 테스트용) → 런타임도 활용

---

## 4. 데이터베이스 스키마

### 4.1 `domain/etf/entity.py`

```python
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Numeric, Text
)
from app.infrastructure.database.session import Base


class ETFPortfolio(Base):
    """사용자별 ETF 포트폴리오 (목표 비중 합산 = 100%)"""
    __tablename__ = "ETF_Portfolios"

    portfolio_id = Column(Integer, primary_key=True, autoincrement=True)
    # ※ report_server_spec 기준: Users 테이블 없음 → ser_no(String)로 식별
    ser_no       = Column(String(50), nullable=False, unique=True)
    name         = Column(String(100), nullable=False)          # 예: "글로벌 분산 포트폴리오"
    total_asset  = Column(Numeric(18, 2), nullable=False)       # 총 자산 (원화)
    created_at   = Column(DateTime, nullable=False)
    updated_at   = Column(DateTime, nullable=False)


class ETFHolding(Base):
    """포트폴리오 내 개별 ETF 보유 항목"""
    __tablename__ = "ETF_Holdings"

    holding_id    = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id  = Column(Integer, ForeignKey("ETF_Portfolios.portfolio_id", ondelete="CASCADE"), nullable=False)
    ticker        = Column(String(20), nullable=False)          # 예: "SPY", "QQQ", "069500"
    name          = Column(String(100))                         # 예: "KODEX 200"
    target_weight = Column(Float, nullable=False)               # 목표 비중 (0.0 ~ 1.0), 합산 1.0
    current_price = Column(Numeric(18, 4))                      # 마지막 조회 시장가
    quantity      = Column(Float, default=0.0)                  # 현재 보유 수량


class RebalancingHistory(Base):
    """리밸런싱 실행 이력 — 커서 페이지네이션 기준 키"""
    __tablename__ = "Rebalancing_History"

    rebalancing_id  = Column(Integer, primary_key=True, autoincrement=True)  # 커서 키
    portfolio_id    = Column(Integer, ForeignKey("ETF_Portfolios.portfolio_id", ondelete="CASCADE"), nullable=False)
    ser_no          = Column(String(50), nullable=False)         # Users FK 없음 → ser_no로 식별
    summary         = Column(Text)          # JSON 직렬화된 주문 플랜 요약
    total_buy_amount  = Column(Numeric(18, 2))
    total_sell_amount = Column(Numeric(18, 2))
    executed_at     = Column(DateTime, nullable=False)
```

> **커서 전략:** `rebalancing_id`는 AutoIncrement로 시간 순서를 보장한다.  
> 최신순 조회 시 `WHERE rebalancing_id < :cursor ORDER BY rebalancing_id DESC LIMIT :limit`.

---

## 5. Pydantic 스키마

### 5.1 `domain/etf/schemas.py`

```python
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
    total_asset: Decimal            # 총 자산 (원화)
    holdings: List[ETFHoldingIn]

    @field_validator("holdings")
    @classmethod
    def weights_sum_to_one(cls, holdings: List[ETFHoldingIn]) -> List[ETFHoldingIn]:
        total = sum(h.target_weight for h in holdings)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"목표 비중 합산이 1.0이어야 합니다 (현재: {total:.4f})")
        return holdings


class RebalanceRequest(BaseModel):
    """리밸런싱 실행 요청 — 최신 시장가를 조회해 주문 플랜을 계산"""
    dry_run: bool = True            # True: 계획만 반환, False: 이력 DB 저장


# ── 응답 스키마 ──────────────────────────────────

class OrderItem(BaseModel):
    ticker: str
    name: str
    action: str                     # "BUY" | "SELL" | "HOLD"
    current_weight: float           # 현재 비중
    target_weight: float            # 목표 비중
    drift: float                    # 괴리율 (current - target)
    amount: Decimal                 # 매수/매도 금액 (원화)
    quantity_change: float          # 매수/매도 수량


class RebalanceResponse(BaseModel):
    portfolio_id: int
    total_asset: Decimal
    orders: List[OrderItem]
    total_buy_amount: Decimal
    total_sell_amount: Decimal
    executed_at: datetime
    dry_run: bool


class HistoryItem(BaseModel):
    rebalancing_id: int             # 커서 값
    total_buy_amount: Decimal
    total_sell_amount: Decimal
    executed_at: datetime
    summary: str                    # 주문 플랜 JSON 요약


class HistoryPageResponse(BaseModel):
    """커서 기반 페이지 응답"""
    items: List[HistoryItem]
    next_cursor: Optional[int]      # None이면 마지막 페이지
    has_next: bool
```

---

## 6. Repository — 커서 페이지네이션 구현

### 6.1 `infrastructure/database/repository/etf_repo.py`

```python
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
        portfolio.name = name
        portfolio.total_asset = total_asset
        portfolio.updated_at = now
        # 기존 홀딩 전체 교체
        db.query(ETFHolding).filter(ETFHolding.portfolio_id == portfolio.portfolio_id).delete()
    else:
        portfolio = ETFPortfolio(
            ser_no=ser_no, name=name,
            total_asset=total_asset,
            created_at=now, updated_at=now,
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


def update_holding_price(db: Session, holding_id: int, price: Decimal):
    db.query(ETFHolding).filter(ETFHolding.holding_id == holding_id).update(
        {"current_price": price}
    )


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
    cursor: Optional[int],  # 마지막으로 받은 rebalancing_id (없으면 첫 페이지)
    limit: int = 10,
) -> Tuple[List[RebalancingHistory], Optional[int]]:
    """
    커서 기반 페이지네이션.

    cursor가 없으면 → 최신 limit+1건 조회
    cursor가 있으면 → rebalancing_id < cursor 조건으로 최신 limit+1건 조회

    limit+1건을 조회해 next_cursor 유무를 판단한다.
    실제 반환은 limit건.
    """
    query = (
        db.query(RebalancingHistory)
        .filter(RebalancingHistory.ser_no == ser_no)
    )

    if cursor is not None:
        # 커서보다 작은 ID만 (= 커서 항목보다 오래된 데이터)
        query = query.filter(RebalancingHistory.rebalancing_id < cursor)

    rows = (
        query
        .order_by(desc(RebalancingHistory.rebalancing_id))
        .limit(limit + 1)           # 다음 페이지 존재 여부 확인용 +1
        .all()
    )

    has_next = len(rows) > limit
    items = rows[:limit]            # 실제 반환 항목
    next_cursor = items[-1].rebalancing_id if has_next else None

    return items, next_cursor
```

---

## 7. 시장가 클라이언트

### 7.1 `infrastructure/market/price_client.py`

```python
import httpx
from typing import Dict
from app.core.config import settings


class PriceClient:
    """
    외부 시장 데이터 API 클라이언트.
    실제 연동 전까지는 더미 가격을 반환하는 fallback 포함.
    """

    DUMMY_PRICES: Dict[str, float] = {
        "SPY":    520.50,
        "QQQ":    430.20,
        "TLT":     92.10,
        "GLD":    220.80,
        "069500": 28450.0,   # KODEX 200
        "360750": 15320.0,   # TIGER 미국S&P500
    }

    def __init__(self):
        self._base_url = getattr(settings, "MARKET_API_URL", "")
        self._api_key  = getattr(settings, "MARKET_API_KEY", "")

    def fetch_prices(self, tickers: list[str]) -> Dict[str, float]:
        """
        tickers 리스트의 현재 시장가를 반환.
        MARKET_API_KEY가 없으면 더미 데이터로 동작.
        """
        if not self._api_key:
            return {t: self.DUMMY_PRICES.get(t, 100.0) for t in tickers}

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{self._base_url}/prices",
                params={"tickers": ",".join(tickers)},
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
            return resp.json()   # {"SPY": 520.5, ...}


price_client = PriceClient()
```

---

## 8. 비즈니스 로직 — 리밸런싱 서비스

### 8.1 `application/etf/rebalance_service.py`

```python
from sqlalchemy.orm import Session
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from datetime import datetime

from app.infrastructure.database.repository import etf_repo
from app.infrastructure.market.price_client import price_client
from app.domain.etf.schemas import (
    CreatePortfolioRequest, RebalanceResponse, OrderItem,
    HistoryPageResponse, HistoryItem,
)


_DRIFT_THRESHOLD = 0.05     # 5% 이상 괴리 시 주문 생성


def create_or_update_portfolio(db: Session, ser_no: str, req: CreatePortfolioRequest):
    """포트폴리오 생성 또는 전체 교체"""
    return etf_repo.upsert_portfolio(
        db, ser_no, req.name, req.total_asset, req.holdings
    )


def calculate_rebalancing(
    db: Session,
    ser_no: str,
    dry_run: bool = True,
) -> RebalanceResponse:
    """
    핵심 리밸런싱 알고리즘:
    1. 포트폴리오 + 보유 ETF 조회
    2. 현재 시장가 fetch
    3. 현재 보유 비중 계산
    4. 목표 비중과 괴리(drift) 계산
    5. 매수/매도 주문 금액 산출
    6. dry_run=False 이면 이력 DB 저장
    """
    portfolio = etf_repo.get_portfolio_by_ser_no(db, ser_no)
    if not portfolio:
        raise ValueError(f"포트폴리오가 없습니다. 먼저 포트폴리오를 생성하세요. (ser_no={ser_no})")

    holdings = etf_repo.get_holdings(db, portfolio.portfolio_id)
    if not holdings:
        raise ValueError("보유 ETF가 없습니다.")

    tickers = [h.ticker for h in holdings]

    # ── Step 1: 시장가 조회 ──
    prices = price_client.fetch_prices(tickers)

    # ── Step 2: 현재 포트폴리오 총 평가액 계산 ──
    total_asset = Decimal(str(portfolio.total_asset))
    holding_values: dict[str, Decimal] = {}
    for h in holdings:
        price = Decimal(str(prices.get(h.ticker, 0)))
        holding_values[h.ticker] = price * Decimal(str(h.quantity))

    current_total = sum(holding_values.values()) or total_asset

    # ── Step 3: 괴리 및 주문 플랜 계산 ──
    orders: List[OrderItem] = []
    total_buy  = Decimal("0")
    total_sell = Decimal("0")

    for h in holdings:
        price = Decimal(str(prices.get(h.ticker, 0)))
        current_value  = holding_values[h.ticker]
        current_weight = float(current_value / current_total) if current_total else 0.0
        target_weight  = h.target_weight
        drift          = round(current_weight - target_weight, 4)

        # 목표 금액
        target_value  = total_asset * Decimal(str(target_weight))
        delta_amount  = target_value - current_value    # 양수: 매수, 음수: 매도

        if abs(drift) < _DRIFT_THRESHOLD:
            action = "HOLD"
            delta_amount = Decimal("0")
        elif delta_amount > 0:
            action = "BUY"
            total_buy += delta_amount
        else:
            action = "SELL"
            total_sell += abs(delta_amount)

        # 수량 변화 (가격이 0이면 0)
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

    # ── Step 4: 이력 저장 (dry_run=False 일 때만) ──
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
```

---

## 9. API 라우터

### 9.1 `interfaces/api/v1/etf_api.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.infrastructure.database.session import get_db
from app.domain.etf.schemas import (
    CreatePortfolioRequest, RebalanceResponse,
    RebalanceRequest, HistoryPageResponse,
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
    사용자 ETF 포트폴리오를 생성하거나 전체 교체합니다.
    - holdings의 target_weight 합산이 1.0이어야 합니다.
    - ser_no: 카메라 시리얼 번호 (Users 테이블 없음, ser_no로 식별)
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
    - 괴리율 5% 미만 ETF는 HOLD 처리
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

    ### 클라이언트 사용법
    1. 첫 요청: `GET /api/v1/etf/rebalance/history/MT-00123?limit=10`
    2. 이후 요청: 응답의 `next_cursor` 값을 `cursor`로 전달
       → `GET /api/v1/etf/rebalance/history/MT-00123?cursor=42&limit=10`
    3. `has_next=false` 이면 마지막 페이지
    """
    try:
        return rebalance_service.get_history_page(db, ser_no, cursor, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 10. main.py 수정

기존 `backend/app/main.py`에 라우터 한 줄 추가:

```python
# 기존 코드
from app.interfaces.api.v1 import report_api, sleep_data_api

# 추가
from app.interfaces.api.v1 import etf_api

# ...기존 include_router 아래에 추가
app.include_router(etf_api.router, prefix="/api/v1/etf", tags=["ETF 리밸런싱"])
```

---

## 11. config.py 수정

```python
class Settings(BaseSettings):
    PROJECT_NAME: str = "M-Take Sleep Analysis"
    GEMINI_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./m_take.db"

    # ETF 시장 데이터 API (없으면 더미 가격 사용)
    MARKET_API_URL: str = ""
    MARKET_API_KEY: str = ""

    class Config:
        env_file = ".env"
```

`.env.example`에도 추가:
```
MARKET_API_URL="https://api.your-market-data.com"
MARKET_API_KEY="your_market_api_key_here"
```

---

## 12. 완성된 API 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/etf/portfolio/{ser_no}` | 포트폴리오 생성/교체 |
| `POST` | `/api/v1/etf/rebalance/{ser_no}` | 리밸런싱 플랜 계산 및 실행 |
| `GET` | `/api/v1/etf/rebalance/history/{ser_no}` | 이력 조회 (커서 페이지네이션) |

---

## 13. 커서 페이지네이션 동작 예시

**첫 페이지 요청:**
```http
GET /api/v1/etf/rebalance/history/MT-00123?limit=3
```
```json
{
  "items": [
    {"rebalancing_id": 50, "total_buy_amount": "150000.00", "executed_at": "2026-04-15T09:00:00"},
    {"rebalancing_id": 48, "total_buy_amount": "80000.00",  "executed_at": "2026-04-08T09:00:00"},
    {"rebalancing_id": 45, "total_buy_amount": "200000.00", "executed_at": "2026-04-01T09:00:00"}
  ],
  "next_cursor": 45,
  "has_next": true
}
```

**다음 페이지 요청** (`next_cursor` 사용):
```http
GET /api/v1/etf/rebalance/history/MT-00123?cursor=45&limit=3
```
```json
{
  "items": [
    {"rebalancing_id": 40, ...},
    {"rebalancing_id": 38, ...}
  ],
  "next_cursor": null,
  "has_next": false
}
```

---

## 14. 구현 순서 (추천)

```
1단계 — 데이터 레이어
  [ ] domain/etf/entity.py 작성
  [ ] domain/etf/schemas.py 작성
  [ ] infrastructure/database/repository/etf_repo.py 작성
      → 커서 페이지네이션 get_rebalancing_history_page() 우선 구현

2단계 — 인프라 연동
  [ ] infrastructure/market/price_client.py 작성
  [ ] core/config.py에 MARKET_API_URL, MARKET_API_KEY 추가

3단계 — 비즈니스 로직
  [ ] application/etf/rebalance_service.py 작성
      → create_or_update_portfolio()
      → calculate_rebalancing()
      → get_history_page()

4단계 — API 레이어
  [ ] interfaces/api/v1/etf_api.py 작성
  [ ] main.py에 etf_api.router 등록

5단계 — 검증
  [ ] uvicorn 실행 후 /docs에서 Swagger UI 확인
  [ ] 포트폴리오 생성 → 리밸런싱 dry_run → 이력 저장 → 커서 페이지네이션 순서로 수동 테스트
  [ ] 더미 데이터로 커서 경계값 테스트 (마지막 페이지 has_next=false 확인)
```

---

## 15. 설계 결정 사항 및 트레이드오프

| 결정 | 이유 |
|------|------|
| 커서 키를 `rebalancing_id`(AutoIncrement)로 선택 | 단조 증가 보장, 인덱스 탐색 O(log n), 시간 역순 정렬과 궁합이 좋음 |
| `limit+1` 조회로 has_next 판단 | COUNT 쿼리 없이 다음 페이지 존재 여부 확인 |
| 괴리 임계값 5% 하드코딩 | 추후 포트폴리오 테이블에 `drift_threshold` 컬럼 추가로 사용자화 가능 |
| 시장가 클라이언트를 싱글턴으로 분리 | 실제 API 키 연동 전 더미로 전체 로직 테스트 가능 |
| `dry_run=True` 기본값 | 실수로 이력이 쌓이는 것 방지, 계획 검토 후 `dry_run=false`로 확정 |
| `upsert_portfolio`에서 기존 홀딩 전체 삭제 후 재삽입 | 부분 업데이트 복잡도 제거, 목표 비중 합산 검증을 Pydantic에서 일괄 처리 |
