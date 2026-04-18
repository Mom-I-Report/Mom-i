from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Numeric, Text
from app.infrastructure.database.session import Base


class ETFPortfolio(Base):
    """사용자별 ETF 포트폴리오 (목표 비중 합산 = 100%)"""
    __tablename__ = "ETF_Portfolios"

    portfolio_id = Column(Integer, primary_key=True, autoincrement=True)
    ser_no       = Column(String(50), nullable=False, unique=True)  # Users 테이블 없음 → ser_no 식별
    name         = Column(String(100), nullable=False)              # 예: "글로벌 분산 포트폴리오"
    total_asset  = Column(Numeric(18, 2), nullable=False)           # 총 자산 (원화)
    created_at   = Column(DateTime, nullable=False)
    updated_at   = Column(DateTime, nullable=False)


class ETFHolding(Base):
    """포트폴리오 내 개별 ETF 보유 항목"""
    __tablename__ = "ETF_Holdings"

    holding_id    = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id  = Column(Integer, ForeignKey("ETF_Portfolios.portfolio_id", ondelete="CASCADE"), nullable=False)
    ticker        = Column(String(20), nullable=False)   # 예: "SPY", "QQQ", "069500"
    name          = Column(String(100))                  # 예: "KODEX 200"
    target_weight = Column(Float, nullable=False)        # 목표 비중 (0.0 ~ 1.0), 합산 1.0
    current_price = Column(Numeric(18, 4))               # 마지막 조회 시장가
    quantity      = Column(Float, default=0.0)           # 현재 보유 수량


class RebalancingHistory(Base):
    """리밸런싱 실행 이력 — 커서 페이지네이션 기준 키"""
    __tablename__ = "Rebalancing_History"

    rebalancing_id    = Column(Integer, primary_key=True, autoincrement=True)  # 커서 키
    portfolio_id      = Column(Integer, ForeignKey("ETF_Portfolios.portfolio_id", ondelete="CASCADE"), nullable=False)
    ser_no            = Column(String(50), nullable=False)
    summary           = Column(Text)           # JSON 직렬화된 주문 플랜 요약
    total_buy_amount  = Column(Numeric(18, 2))
    total_sell_amount = Column(Numeric(18, 2))
    executed_at       = Column(DateTime, nullable=False)
