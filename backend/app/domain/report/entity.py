from sqlalchemy import Column, Integer, String, Date, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class WeeklyData(Base):
    """맘아이 서버로부터 받은 주간 원본 데이터 — AI 컨텍스트(3주 트렌드)용"""
    __tablename__ = "Weekly_Data"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    ser_no     = Column(String(50), nullable=False)
    week_start = Column(Date, nullable=False)
    sleep_json = Column(JSON, nullable=False)   # [{date, sleep_min, restless_min}, ...]
    env_json   = Column(JSON, nullable=False)   # {temp_avg, temp_max, temp_min, db_max, db_avg}
    event_json = Column(JSON, nullable=False)   # {cry_count, leave_count}
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ser_no", "week_start", name="uq_weekly_ser_week"),
    )


class GeneratedReport(Base):
    """생성된 리포트 — 사용자 재열람 + AI 이전 조언 참고용"""
    __tablename__ = "Generated_Reports"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    ser_no      = Column(String(50), nullable=False)
    week_start  = Column(Date, nullable=False)
    report_json = Column(JSON, nullable=False)   # 최종 리포트 전체 (응답 구조 그대로)
    ai_comment  = Column(Text, nullable=False)
    created_at  = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ser_no", "week_start", name="uq_report_ser_week"),
    )
