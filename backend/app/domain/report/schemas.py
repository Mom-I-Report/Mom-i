"""
schemas.py — 리포트 서버 Pydantic 스키마 전체 정의

데이터 흐름별 구분:
  [요청] 맘아이 서버 → 리포트 서버  : GenerateReportRequest 및 하위 모델
  [응답] 리포트 서버 → 맘아이 서버  : GenerateReportResponse 및 하위 모델
  [목록] 앱 → 리포트 서버           : ReportListResponse (카드형 요약)
  [상세] 앱 → 리포트 서버           : ReportDetailResponse (전체 필드)

EMTAKE 프로토콜 → 맘아이 서버 → 리포트 서버 데이터 변환 책임:
  - SleepData.day_gs "4h50m" → sleep_min(분 정수) 변환: 맘아이 서버 담당
  - SleepData.month_gs "3h45m" → month_sleep_h(시간 float) 변환: 맘아이 서버 담당
  - EMTAKE Breath(호흡수), Temp(체온 상승), IndoorTemp, dB: 맘아이 서버가 수집 후 push

extra='ignore': relay 서버 데이터 확장(시니어 등)에 대비해 알 수 없는 필드는 조용히 무시한다.
"""
from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Literal, Optional
from datetime import date, datetime


# ── 요청: 맘아이 서버 → 리포트 서버 ─────────────────────────────────────────

class SleepSession(BaseModel):
    """
    하나의 수면 구간 (밤잠 or 낮잠).
    EMTAKE SleepData.sessions[] 단건에 대응.
    is_nap: start 시각이 21:00 이전이면 낮잠으로 분류.
    """
    model_config = ConfigDict(extra='ignore')

    start: str          # "23:45"
    end: str            # "06:23"
    duration_min: int   # 398
    wake_up: int        # 해당 구간 뒤척임 횟수
    is_nap: bool = False


class SleepDay(BaseModel):
    """
    하루치 수면 데이터.
    sleep_min / restless_min 은 필수.
    수면 단계 필드(awake_min 등)는 relay 확장 시 추가되는 선택 항목.
    """
    model_config = ConfigDict(extra='ignore')

    date: date
    sleep_min: int
    restless_min: int
    awake_min: Optional[int] = None         # 깨어있음
    deep_sleep_min: Optional[int] = None    # 깊은 수면
    rem_sleep_min: Optional[int] = None     # 렘수면
    light_sleep_min: Optional[int] = None   # 얕은 수면
    wake_time_min: Optional[int] = None     # 깬 시간
    wakeup_count: Optional[int] = None      # 총 뒤척임 횟수 (day_wakeup)
    device_status: Optional[str] = None     # 기기 판단 상태 (NORMAL / CAUTION 등)
    sessions: Optional[List[SleepSession]] = None  # 수면 세션 상세
    # 일별 환경 데이터 (mom-i 서버 제공 시 포함 — 일별 수면-환경 상관관계 분석용)
    env_temp_max: Optional[float] = None    # 당일 최고 실내 온도 (°C)
    env_db_max: Optional[int] = None        # 당일 최고 소음 (dB)
    env_humidity_avg: Optional[float] = None  # 당일 평균 습도 (%)
    env_bright_avg: Optional[float] = None  # 당일 평균 조도 (lux)


class EnvironmentData(BaseModel):
    """실내 환경 집계 데이터. EMTAKE CMD: IndoorTemp + dB + Humidity + Bright."""
    model_config = ConfigDict(extra='ignore')

    temp_avg: float
    temp_max: float
    temp_min: float
    db_max: int
    db_avg: int
    humidity_min: Optional[float] = None
    humidity_max: Optional[float] = None
    humidity_avg: Optional[float] = None
    bright_min: Optional[float] = None
    bright_max: Optional[float] = None
    bright_avg: Optional[float] = None


class BreathData(BaseModel):
    """수면 중 호흡수 데이터. EMTAKE CMD: Breath. 단위: 회/분."""
    model_config = ConfigDict(extra='ignore')

    breath_min: int
    breath_max: int
    breath_avg: int


class BodyTempData(BaseModel):
    """수면 중 체온 상승 데이터. EMTAKE CMD: Temp. 단위: °C 델타값."""
    model_config = ConfigDict(extra='ignore')

    body_temp_min: float
    body_temp_max: float
    body_temp_avg: float


class MonthlySummary(BaseModel):
    """월간/주간 수면 집계 데이터. EMTAKE CMD: SleepData month_gs/pr + week_gs/pr."""
    model_config = ConfigDict(extra='ignore')

    month_sleep_h: float
    month_restless_h: float
    week_sleep_h: Optional[float] = None
    week_restless_h: Optional[float] = None


class EventData(BaseModel):
    """수면 중 이벤트 횟수 (울음 감지, 카메라 이탈)."""
    model_config = ConfigDict(extra='ignore')

    cry_count: int
    leave_count: int


class GenerateReportRequest(BaseModel):
    """
    맘아이 서버가 리포트 서버에 push하는 주간 데이터 요청 모델.

    ser_no          : 기기 시리얼 번호 — 유일한 식별자 (개인정보 없음)
    baby_age_months : 월령 — 맘아이 서버가 생년월일 기반 계산 후 전달
    week_start      : 리포트 대상 주 시작일 (반드시 월요일)
    sleep           : 7일치 수면 데이터 (validator로 7개 강제)
    user_type       : "baby"(유아) | "senior" — EMTAKE Type 코드 구분값
    """
    model_config = ConfigDict(extra='ignore')

    ser_no: str
    baby_name: Optional[str] = None
    baby_gender: Optional[str] = None   # "M" | "F"
    baby_age_months: int
    week_start: date
    sleep: List[SleepDay]
    environment: EnvironmentData
    breath: BreathData
    body_temp: BodyTempData
    monthly: MonthlySummary
    events: EventData
    user_type: Literal["baby", "senior"] = "baby"

    @field_validator("sleep")
    @classmethod
    def sleep_must_be_7_days(cls, v: List[SleepDay]) -> List[SleepDay]:
        if len(v) != 7:
            raise ValueError(f"sleep 데이터는 7일치여야 합니다 (현재: {len(v)}일)")
        return v


# ── 응답 공통 하위 모델 ───────────────────────────────────────────────────────

class DailySummary(BaseModel):
    """일별 수면 요약 — 앱 UI의 일별 차트·목록에 사용."""
    model_config = ConfigDict(extra='ignore')

    date: date
    day: str
    sleep_h: float
    restless_min: int
    wakeup_count: Optional[int] = None
    sessions: Optional[List[SleepSession]] = None


class TrendData(BaseModel):
    """
    지난 주 대비 변화량. 이전 데이터가 없으면 None.
    양수(+) = 이번 주가 지난 주보다 증가/높음.
    """
    model_config = ConfigDict(extra='ignore')

    sleep_vs_last_week: float
    restless_vs_last_week: int
    cry_vs_last_week: int
    breath_vs_last_week: int
    body_temp_vs_last_week: float


class BreathSummary(BaseModel):
    """호흡수 분석 결과. is_normal은 AAP 기준 월령별 범위로 판정."""
    model_config = ConfigDict(extra='ignore')

    breath_min: int
    breath_max: int
    breath_avg: int
    is_normal: bool
    normal_range: str


class BodyTempSummary(BaseModel):
    """체온 분석 결과. status: "정상" | "미열 주의" | "발열 의심"."""
    model_config = ConfigDict(extra='ignore')

    body_temp_min: float
    body_temp_max: float
    body_temp_avg: float
    status: str


class ReportSummary(BaseModel):
    """주간 핵심 요약 지표."""
    model_config = ConfigDict(extra='ignore')

    avg_sleep_h: float
    avg_restless_min: int
    cry_count: int
    leave_count: int
    temp_avg: float
    db_max: int
    month_sleep_h: float
    month_restless_h: float
    week_sleep_h: Optional[float] = None
    week_restless_h: Optional[float] = None
    humidity_min: Optional[float] = None
    humidity_max: Optional[float] = None
    humidity_avg: Optional[float] = None
    bright_avg: Optional[float] = None
    nap_count: Optional[int] = None     # 주간 낮잠 세션 수 합계


class AiCommentItem(BaseModel):
    """AI 분석 팁 단건. 프론트 카드 1개에 대응."""
    model_config = ConfigDict(extra='ignore')

    type: str               # "caution" | "good" | "tip" | "developmental"
    icon: Optional[str] = None
    title: str
    text: str


class SleepGuide(BaseModel):
    """AI가 추천하는 수면 교육법."""
    model_config = ConfigDict(extra='ignore')

    method_name: str                    # 교육법 이름 (예: "퍼버법", "의자법")
    title: str                          # 솔루션 제목 ("✨ 추천 솔루션: '퍼버법'을 활용한 ...")
    reason: str                         # 추천 이유 (데이터 근거 포함)
    steps: List[str]                    # 단계별 실행 가이드 (3단계)
    kick_action: Optional[str] = None   # 오늘 바로 실행할 핵심 행동 1가지


class AgeKick(BaseModel):
    """월령별 주요 발달 이슈."""
    model_config = ConfigDict(extra='ignore')

    title: str              # 이슈 제목 (예: "8개월 분리불안")
    text: str               # 이슈 설명 + 부모 대처 팁
    is_wonder_weeks: bool   # 원더윅스 해당 여부


# ── 리포트 생성 응답 ─────────────────────────────────────────────────────────

class GenerateReportResponse(BaseModel):
    """
    POST /reports/generate 응답 및 DB 저장 기준 구조.

    ai_comment      : AI 분석 팁 목록 [{type, icon, title, text}] (Gemini 생성)
    sleep_guide     : 추천 수면 교육법 (Gemini 생성)
    age_kick        : 월령별 발달 이슈 (Gemini 생성)
    parent_message  : 부모 응원 메시지 — 리포트 공유 시 함께 전송 (Gemini 생성)
    trend           : 이전 데이터 없으면 null
    """
    model_config = ConfigDict(extra='ignore')

    ser_no: str
    week_start: date
    week_label: str
    generated_at: datetime
    baby_name: Optional[str] = None
    baby_gender: Optional[str] = None
    baby_age_months: int = 0
    summary: ReportSummary
    breath: BreathSummary
    body_temp: BodyTempSummary
    daily: List[DailySummary]
    trend: Optional[TrendData]
    ai_comment: List[AiCommentItem]
    sleep_guide: Optional[SleepGuide] = None
    age_kick: Optional[AgeKick] = None
    parent_message: Optional[str] = None


# ── 앱 전용 응답: 목록(카드형) ────────────────────────────────────────────────

class ReportListItem(BaseModel):
    """
    GET /reports 응답의 단건 카드.
    목록 화면에서 필요한 요약 정보만 포함해 네트워크를 절약한다.
    """
    model_config = ConfigDict(extra='ignore')

    report_id: int
    week_start: date
    week_label: str
    avg_sleep_h: float
    avg_restless_min: int
    sleep_guide_method: Optional[str] = None   # sleep_guide.method_name


class ReportListResponse(BaseModel):
    """GET /reports 응답."""
    model_config = ConfigDict(extra='ignore')

    reports: List[ReportListItem]
    total: int


# ── 앱 전용 응답: 상세 ────────────────────────────────────────────────────────

class ReportDetailResponse(BaseModel):
    """
    GET /reports/{report_id} 응답.
    프론트 report.html 전체 렌더링에 필요한 모든 필드 포함.
    """
    model_config = ConfigDict(extra='ignore')

    report_id: int
    ser_no: str
    week_start: date
    week_label: str
    generated_at: datetime
    summary: ReportSummary
    breath: BreathSummary
    body_temp: BodyTempSummary
    daily: List[DailySummary]
    trend: Optional[TrendData]
    ai_comment: List[AiCommentItem]
    sleep_guide: Optional[SleepGuide] = None
    age_kick: Optional[AgeKick] = None
    parent_message: Optional[str] = None
