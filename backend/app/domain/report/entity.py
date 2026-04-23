"""
entity.py — SQLAlchemy ORM 모델 정의

이 서버가 운영하는 테이블: 2개
  - Weekly_Data       : 맘아이 서버로부터 받은 주간 원본 데이터
  - Generated_Reports : AI가 생성한 최종 리포트

설계 원칙:
  - 개인정보(이름·생년월일·이메일) 일절 저장하지 않음
  - ser_no(카메라 시리얼 번호) 만 사용자 식별자로 사용
  - UNIQUE KEY (ser_no, week_start) → 동일 주차 재전송 시 upsert
  - rolling 삭제: 3주치 초과 데이터는 매주 물리 삭제 (소프트 삭제 없음)

주의:
  SQLAlchemy create_all()은 테이블을 새로 만들 뿐 ALTER TABLE은 수행하지 않음.
  컬럼 추가 시 기존 SQLite DB를 삭제하거나 Alembic 마이그레이션으로 적용해야 함.
"""
from sqlalchemy import Column, Integer, String, Date, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class WeeklyData(Base):
    """
    맘아이 서버로부터 push된 주간 원본 데이터 저장 테이블.

    저장 목적:
      AI 컨텍스트 구성 시 최대 3주치 이전 데이터를 참조해 트렌드를 분석하기 위함.
      리포트 생성 후에도 원본은 보존해 다음 주 AI 컨텍스트에서 재사용됨.

    JSON 컬럼 구조:
      sleep_json     : [{date, sleep_min, restless_min}, ...] — 7일치
      env_json       : {temp_avg, temp_max, temp_min, db_max, db_avg}
      event_json     : {cry_count, leave_count}
      breath_json    : {breath_min, breath_max, breath_avg}
      body_temp_json : {body_temp_min, body_temp_max, body_temp_avg}
      monthly_json   : {month_sleep_h, month_restless_h}

    보존 기간:
      12주 초과 시 매주 월요일 10:00 KST 스케줄러가 물리 삭제. (AI 고도화 컨텍스트용)
    """
    __tablename__ = "Weekly_Data"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    ser_no         = Column(String(50), nullable=False)               # 기기 시리얼 번호
    week_start     = Column(Date, nullable=False)                      # 주 시작일 (월요일)
    sleep_json     = Column(JSON, nullable=False)                      # 7일치 수면 데이터
    env_json       = Column(JSON, nullable=False)                      # 실내 환경 (온도·소음)
    event_json     = Column(JSON, nullable=False)                      # 이벤트 (울음·이탈)
    breath_json    = Column(JSON, nullable=False)                      # 호흡수 (회/분)
    body_temp_json = Column(JSON, nullable=False)                      # 체온 상승 (°C)
    monthly_json   = Column(JSON, nullable=False)                      # 월간 집계
    created_at     = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ser_no", "week_start", name="uq_weekly_ser_week"),
    )


class GeneratedReport(Base):
    """
    AI가 생성한 최종 리포트 저장 테이블.

    저장 목적:
      - 사용자 앱 재열람: GET /history/{ser_no} 에서 최근 3주치 반환
      - 향후 기능: 이전 주 AI 조언을 참고해 연속성 있는 코멘트 생성에 활용 가능

    report_json:
      GenerateReportResponse 전체를 JSON으로 직렬화 저장.
      summary, breath, body_temp, daily, trend, ai_comment 모두 포함.

    ai_comment:
      report_json 내 ai_comment 필드와 동일한 값이지만,
      향후 이전 조언 참조 기능 구현 시 빠른 접근을 위해 별도 컬럼으로 분리.

    보존 기간:
      5주 초과 시 매주 월요일 10:00 KST 스케줄러가 물리 삭제. (앱 3주 열람 + 여유 2주)
    """
    __tablename__ = "Generated_Reports"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    ser_no      = Column(String(50), nullable=False)                   # 기기 시리얼 번호
    week_start  = Column(Date, nullable=False)                         # 주 시작일 (월요일)
    report_json = Column(JSON, nullable=False)                         # 최종 리포트 전체 JSON
    ai_comment  = Column(Text, nullable=False)                         # AI 조언 텍스트 (빠른 접근용)
    created_at  = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ser_no", "week_start", name="uq_report_ser_week"),
    )
