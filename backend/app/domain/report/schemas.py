from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime


# ── 요청: 맘아이 서버 → 리포트 서버 ──────────────────────

class SleepDay(BaseModel):
    date: date
    sleep_min: int      # 수면 시간 (분 단위 정수, 예: 570 = 9시간 30분)
    restless_min: int   # 뒤척임 시간 (분)


class EnvironmentData(BaseModel):
    temp_avg: float
    temp_max: float
    temp_min: float
    db_max: int         # 최대 소음 (dB)
    db_avg: int         # 평균 소음 (dB)


class EventData(BaseModel):
    cry_count: int
    leave_count: int


class GenerateReportRequest(BaseModel):
    ser_no: str                     # 기기 식별자 (개인정보 없음)
    baby_age_months: int            # 월령 — 맘아이 서버가 계산해서 넘김
    week_start: date                # 리포트 대상 주 시작일 (월요일)
    sleep: List[SleepDay]          # 7일치 수면 데이터
    environment: EnvironmentData
    events: EventData

    @field_validator("sleep")
    @classmethod
    def sleep_must_be_7_days(cls, v: List[SleepDay]) -> List[SleepDay]:
        if len(v) != 7:
            raise ValueError(f"sleep 데이터는 7일치여야 합니다 (현재: {len(v)}일)")
        return v


# ── 응답: 리포트 서버 → 맘아이 서버 ──────────────────────

class DailySummary(BaseModel):
    date: date
    day: str            # "월", "화", "수" ...
    sleep_h: float      # 수면 시간 (시간, 소수점 1자리)
    restless_min: int


class TrendData(BaseModel):
    sleep_vs_last_week: float       # 지난주 대비 평균 수면 변화 (시간)
    restless_vs_last_week: int      # 지난주 대비 뒤척임 변화 (분)
    cry_vs_last_week: int


class ReportSummary(BaseModel):
    avg_sleep_h: float
    avg_restless_min: int
    cry_count: int
    leave_count: int
    temp_avg: float
    db_max: int


class GenerateReportResponse(BaseModel):
    ser_no: str
    week_start: date
    week_label: str                 # "2026년 4월 2주차"
    generated_at: datetime
    summary: ReportSummary
    daily: List[DailySummary]
    trend: Optional[TrendData]      # 이전 데이터 없으면 None
    ai_comment: str


# ── 이력 조회: 앱 → 리포트 서버 ──────────────────────────

class ReportItem(BaseModel):
    week_start: date
    week_label: str
    report_json: Dict[str, Any]


class ReportHistoryResponse(BaseModel):
    reports: List[ReportItem]
    total: int
