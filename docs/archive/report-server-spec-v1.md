# 맘아이 리포트 서버 구현 스펙

> ⚠ **[DEPRECATED]** 이 문서는 2026-04-15 기준 초기 구현 스펙이며, 현재 코드와 다릅니다.  
> 최신 상태는 [`research.md`](./research.md) 및 [`plan.md`](./plan.md)를 참조하세요.  
> 주요 차이점: async 전환 없음 / breath·body_temp·monthly 필드 없음 / 4섹션(현재 5섹션) / gemini-1.5-flash(현재 2.5)

> 브랜치: `feat/report-server`  
> 스택: FastAPI + SQLAlchemy + MySQL + Google Gemini API  
> 역할: 맘아이 서버로부터 주간 수면 데이터를 받아 AI 리포트를 생성·저장·리턴

---

## 1. 이 서버가 하는 일 (딱 3가지)

1. 맘아이 서버가 구독 유저 데이터를 **push** → AI 리포트 JSON 생성 후 즉시 리턴
2. 생성된 리포트를 **3주치** DB에 보관
3. 사용자가 앱에서 이전 리포트 **재열람** 요청 시 리턴

```
맘아이 서버 → POST /report/generate → 리포트 JSON 리턴
앱(사용자)  → GET  /report/{ser_no} → 최근 3주치 리포트 리턴
```

> **개인정보 없음**: `baby_name`, `email` 등은 일절 받지 않는다.  
> `ser_no`(카메라 시리얼 번호)만 사용자 식별자로 사용한다.

---

## 2. 디렉토리 구조

기존 클린 아키텍처(4레이어)를 그대로 따른다.

```
backend/app/
├── domain/report/
│   ├── __init__.py
│   ├── entity.py          ← ORM 모델 (Weekly_Data, Generated_Reports)
│   └── schemas.py         ← Pydantic 요청/응답 스키마
├── application/report/
│   ├── __init__.py
│   └── report_service.py  ← 리포트 생성 비즈니스 로직
├── infrastructure/
│   ├── database/repository/
│   │   └── report_repo.py ← DB 접근 (저장, 3주치 조회, rolling 삭제)
│   └── llm/
│       └── gemini_client.py ← Gemini API 호출 (기존 파일 수정)
└── interfaces/api/v1/
    └── report_api.py      ← FastAPI 라우터 (기존 파일 교체)
```

수정 파일:
- `backend/app/main.py` — 라우터 재등록
- `backend/app/core/config.py` — 환경변수 확인

---

## 3. DB 스키마

### 3.1 `domain/report/entity.py`

```python
from sqlalchemy import Column, Integer, String, Date, Text, JSON, TIMESTAMP
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class WeeklyData(Base):
    """맘아이 서버로부터 받은 주간 원본 데이터 — AI 컨텍스트(3주 트렌드)용"""
    __tablename__ = "Weekly_Data"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    ser_no      = Column(String(50), nullable=False)      # 기기 식별자
    week_start  = Column(Date, nullable=False)             # 리포트 대상 주 시작일
    sleep_json  = Column(JSON, nullable=False)             # 7일치 수면 데이터
    env_json    = Column(JSON, nullable=False)             # 환경 집계
    event_json  = Column(JSON, nullable=False)             # 이벤트 집계
    created_at  = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )
    # UNIQUE KEY (ser_no, week_start) — Alembic 마이그레이션에서 추가


class GeneratedReport(Base):
    """생성된 리포트 — 사용자 재열람 + AI 이전 조언 참고용"""
    __tablename__ = "Generated_Reports"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    ser_no       = Column(String(50), nullable=False)
    week_start   = Column(Date, nullable=False)
    report_json  = Column(JSON, nullable=False)            # 최종 리포트 전체
    ai_comment   = Column(Text, nullable=False)            # AI 조언 텍스트
    created_at   = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )
    # UNIQUE KEY (ser_no, week_start) — Alembic 마이그레이션에서 추가
```

> **UNIQUE KEY**는 entity.py의 `__table_args__`에 `UniqueConstraint`로 추가하거나  
> Alembic 마이그레이션 파일에서 직접 추가한다.

---

## 4. Pydantic 스키마

### 4.1 `domain/report/schemas.py`

```python
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime


# ── 요청: 맘아이 서버 → 우리 서버 ──────────────────────

class SleepDay(BaseModel):
    date: date
    sleep_min: int        # 수면 시간 (분 단위 정수, 예: 570 = 9시간 30분)
    restless_min: int     # 뒤척임 시간 (분)


class EnvironmentData(BaseModel):
    temp_avg: float
    temp_max: float
    temp_min: float
    db_max: int           # 최대 소음 (dB)
    db_avg: int           # 평균 소음 (dB)


class EventData(BaseModel):
    cry_count: int
    leave_count: int


class GenerateReportRequest(BaseModel):
    ser_no: str                        # 기기 식별자 (개인정보 없음)
    baby_age_months: int               # 월령 — 맘아이 서버가 계산해서 넘김
    week_start: date                   # 리포트 대상 주 시작일 (월요일)
    sleep: List[SleepDay]             # 7일치 수면 데이터
    environment: EnvironmentData
    events: EventData

    @field_validator("sleep")
    @classmethod
    def sleep_must_be_7_days(cls, v: List[SleepDay]) -> List[SleepDay]:
        if len(v) != 7:
            raise ValueError(f"sleep 데이터는 7일치여야 합니다 (현재: {len(v)}일)")
        return v


# ── 응답: 우리 서버 → 맘아이 서버 ──────────────────────

class DailySummary(BaseModel):
    date: date
    day: str              # "월", "화", "수" ...
    sleep_h: float        # 수면 시간 (시간, 소수점 1자리)
    restless_min: int


class TrendData(BaseModel):
    sleep_vs_last_week: float      # 지난주 대비 평균 수면 변화 (시간)
    restless_vs_last_week: int     # 지난주 대비 뒤척임 변화 (분)
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
    week_label: str                    # "2026년 4월 2주차"
    generated_at: datetime
    summary: ReportSummary
    daily: List[DailySummary]
    trend: Optional[TrendData]         # 이전 데이터 없으면 None
    ai_comment: str


# ── 이력 조회: 앱 → 우리 서버 ──────────────────────────

class ReportItem(BaseModel):
    week_start: date
    week_label: str
    report_json: Dict[str, Any]


class ReportHistoryResponse(BaseModel):
    reports: List[ReportItem]
    total: int
```

---

## 5. Repository

### 5.1 `infrastructure/database/repository/report_repo.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, timedelta
from typing import List, Optional
import json

from app.domain.report.entity import WeeklyData, GeneratedReport


# ── Weekly_Data ─────────────────────────────────────

def save_weekly_data(
    db: Session,
    ser_no: str,
    week_start: date,
    sleep_json: list,
    env_json: dict,
    event_json: dict,
) -> WeeklyData:
    """주간 원본 데이터 저장 (upsert)"""
    existing = db.query(WeeklyData).filter(
        and_(WeeklyData.ser_no == ser_no, WeeklyData.week_start == week_start)
    ).first()

    if existing:
        existing.sleep_json = sleep_json
        existing.env_json = env_json
        existing.event_json = event_json
    else:
        existing = WeeklyData(
            ser_no=ser_no,
            week_start=week_start,
            sleep_json=sleep_json,
            env_json=env_json,
            event_json=event_json,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def get_recent_weekly_data(
    db: Session,
    ser_no: str,
    week_start: date,
    weeks: int = 2,
) -> List[WeeklyData]:
    """이전 N주치 데이터 조회 — AI 컨텍스트용"""
    cutoff = week_start - timedelta(weeks=weeks)
    return (
        db.query(WeeklyData)
        .filter(
            and_(
                WeeklyData.ser_no == ser_no,
                WeeklyData.week_start >= cutoff,
                WeeklyData.week_start < week_start,  # 이번 주 제외
            )
        )
        .order_by(WeeklyData.week_start.desc())
        .all()
    )


# ── Generated_Reports ───────────────────────────────

def save_report(
    db: Session,
    ser_no: str,
    week_start: date,
    report_json: dict,
    ai_comment: str,
) -> GeneratedReport:
    """리포트 저장 (upsert)"""
    existing = db.query(GeneratedReport).filter(
        and_(GeneratedReport.ser_no == ser_no, GeneratedReport.week_start == week_start)
    ).first()

    if existing:
        existing.report_json = report_json
        existing.ai_comment = ai_comment
    else:
        existing = GeneratedReport(
            ser_no=ser_no,
            week_start=week_start,
            report_json=report_json,
            ai_comment=ai_comment,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def get_recent_reports(
    db: Session,
    ser_no: str,
    limit: int = 3,
) -> List[GeneratedReport]:
    """최근 3주치 리포트 조회"""
    cutoff = date.today() - timedelta(weeks=3)
    return (
        db.query(GeneratedReport)
        .filter(
            and_(
                GeneratedReport.ser_no == ser_no,
                GeneratedReport.week_start >= cutoff,
            )
        )
        .order_by(GeneratedReport.week_start.desc())
        .limit(limit)
        .all()
    )


# ── Rolling 삭제 (매주 스케줄러에서 호출) ──────────────

def delete_old_data(db: Session) -> None:
    """3주치 초과 데이터 자동 삭제"""
    cutoff = date.today() - timedelta(weeks=3)
    db.query(WeeklyData).filter(WeeklyData.week_start < cutoff).delete()
    db.query(GeneratedReport).filter(GeneratedReport.week_start < cutoff).delete()
    db.commit()
```

---

## 6. 비즈니스 로직

### 6.1 `application/report/report_service.py`

```python
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from app.domain.report.schemas import (
    GenerateReportRequest, GenerateReportResponse,
    ReportSummary, DailySummary, TrendData,
    ReportHistoryResponse, ReportItem,
)
from app.infrastructure.database.repository import report_repo
from app.infrastructure.llm.gemini_client import generate_insight

_DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def _week_label(week_start: date) -> str:
    """날짜 → '2026년 4월 2주차' 형식"""
    week_num = (week_start.day - 1) // 7 + 1
    return f"{week_start.year}년 {week_start.month}월 {week_num}주차"


def _build_summary(req: GenerateReportRequest) -> ReportSummary:
    sleep_mins = [s.sleep_min for s in req.sleep]
    restless_mins = [s.restless_min for s in req.sleep]
    return ReportSummary(
        avg_sleep_h=round(sum(sleep_mins) / len(sleep_mins) / 60, 1),
        avg_restless_min=round(sum(restless_mins) / len(restless_mins)),
        cry_count=req.events.cry_count,
        leave_count=req.events.leave_count,
        temp_avg=req.environment.temp_avg,
        db_max=req.environment.db_max,
    )


def _build_daily(req: GenerateReportRequest):
    result = []
    for s in req.sleep:
        result.append(DailySummary(
            date=s.date,
            day=_DAY_KO[s.date.weekday()],
            sleep_h=round(s.sleep_min / 60, 1),
            restless_min=s.restless_min,
        ))
    return result


def _build_trend(db: Session, req: GenerateReportRequest, summary: ReportSummary) -> Optional[TrendData]:
    """이전 주 데이터가 있으면 트렌드 계산"""
    prev_data = report_repo.get_recent_weekly_data(db, req.ser_no, req.week_start, weeks=1)
    if not prev_data:
        return None

    prev = prev_data[0]
    prev_sleeps = [s["sleep_min"] for s in prev.sleep_json]
    prev_restless = [s["restless_min"] for s in prev.sleep_json]
    prev_avg_sleep_h = round(sum(prev_sleeps) / len(prev_sleeps) / 60, 1)
    prev_avg_restless = round(sum(prev_restless) / len(prev_restless))
    prev_cry = prev.event_json.get("cry_count", 0)

    return TrendData(
        sleep_vs_last_week=round(summary.avg_sleep_h - prev_avg_sleep_h, 1),
        restless_vs_last_week=summary.avg_restless_min - prev_avg_restless,
        cry_vs_last_week=summary.cry_count - prev_cry,
    )


def _build_ai_context(
    req: GenerateReportRequest,
    summary: ReportSummary,
    trend: Optional[TrendData],
    db: Session,
) -> dict:
    """Gemini에 넘길 컨텍스트 구성 — 최대 3주치 포함"""
    ctx = {
        "baby_age_months": req.baby_age_months,
        "week_label": _week_label(req.week_start),
        "this_week": {
            "avg_sleep_h": summary.avg_sleep_h,
            "avg_restless_min": summary.avg_restless_min,
            "cry_count": summary.cry_count,
            "temp_avg": req.environment.temp_avg,
            "db_max": req.environment.db_max,
        },
    }

    prev_data = report_repo.get_recent_weekly_data(db, req.ser_no, req.week_start, weeks=2)
    if len(prev_data) >= 1:
        p = prev_data[0]
        ps = [s["sleep_min"] for s in p.sleep_json]
        pr = [s["restless_min"] for s in p.sleep_json]
        ctx["last_week"] = {
            "avg_sleep_h": round(sum(ps) / len(ps) / 60, 1),
            "avg_restless_min": round(sum(pr) / len(pr)),
            "cry_count": p.event_json.get("cry_count", 0),
        }
    if len(prev_data) >= 2:
        p2 = prev_data[1]
        ps2 = [s["sleep_min"] for s in p2.sleep_json]
        pr2 = [s["restless_min"] for s in p2.sleep_json]
        ctx["two_weeks_ago"] = {
            "avg_sleep_h": round(sum(ps2) / len(ps2) / 60, 1),
            "avg_restless_min": round(sum(pr2) / len(pr2)),
            "cry_count": p2.event_json.get("cry_count", 0),
        }

    return ctx


# ── Public API ─────────────────────────────────────

def generate_report(db: Session, req: GenerateReportRequest) -> GenerateReportResponse:
    """
    1. 원본 데이터 저장 (AI 컨텍스트용)
    2. 요약 / 일별 / 트렌드 계산
    3. Gemini AI 조언 생성
    4. 리포트 저장 후 리턴
    """
    # Step 1 — 원본 저장
    report_repo.save_weekly_data(
        db=db,
        ser_no=req.ser_no,
        week_start=req.week_start,
        sleep_json=[s.model_dump(mode="json") for s in req.sleep],
        env_json=req.environment.model_dump(),
        event_json=req.events.model_dump(),
    )

    # Step 2 — 집계
    summary = _build_summary(req)
    daily = _build_daily(req)
    trend = _build_trend(db, req, summary)

    # Step 3 — AI 조언
    ai_context = _build_ai_context(req, summary, trend, db)
    ai_comment = generate_insight(ai_context)

    # Step 4 — 리포트 저장
    week_label = _week_label(req.week_start)
    report_data = GenerateReportResponse(
        ser_no=req.ser_no,
        week_start=req.week_start,
        week_label=week_label,
        generated_at=datetime.now(),
        summary=summary,
        daily=daily,
        trend=trend,
        ai_comment=ai_comment,
    )

    report_repo.save_report(
        db=db,
        ser_no=req.ser_no,
        week_start=req.week_start,
        report_json=report_data.model_dump(mode="json"),
        ai_comment=ai_comment,
    )

    return report_data


def get_report_history(db: Session, ser_no: str) -> ReportHistoryResponse:
    """최근 3주치 리포트 이력 조회"""
    reports = report_repo.get_recent_reports(db, ser_no, limit=3)
    if not reports:
        raise ValueError("조회 가능한 리포트가 없습니다.")

    items = [
        ReportItem(
            week_start=r.week_start,
            week_label=_week_label(r.week_start),
            report_json=r.report_json,
        )
        for r in reports
    ]
    return ReportHistoryResponse(reports=items, total=len(items))
```

---

## 7. Gemini 클라이언트 수정

### 7.1 `infrastructure/llm/gemini_client.py` — 기존 파일 수정

기존 `generate_insight()` 함수의 입력 파라미터를 아래 구조로 맞춘다.

```python
def generate_insight(ctx: dict) -> str:
    """
    ctx 구조:
    {
        "baby_age_months": 8,
        "week_label": "2026년 4월 2주차",
        "this_week": { "avg_sleep_h": 9.1, "avg_restless_min": 25, "cry_count": 3, "temp_avg": 23.1, "db_max": 62 },
        "last_week": { ... },        # 있으면 포함
        "two_weeks_ago": { ... },    # 있으면 포함
    }
    """
    prompt = f"""
다음은 생후 {ctx['baby_age_months']}개월 아기의 {ctx['week_label']} 수면 데이터입니다.

[이번 주]
- 평균 수면: {ctx['this_week']['avg_sleep_h']}시간
- 평균 뒤척임: {ctx['this_week']['avg_restless_min']}분
- 울음 횟수: {ctx['this_week']['cry_count']}회
- 평균 온도: {ctx['this_week']['temp_avg']}°C / 최대 소음: {ctx['this_week']['db_max']}dB
"""
    if "last_week" in ctx:
        lw = ctx["last_week"]
        prompt += f"""
[지난 주]
- 평균 수면: {lw['avg_sleep_h']}시간 / 뒤척임: {lw['avg_restless_min']}분 / 울음: {lw['cry_count']}회
"""
    if "two_weeks_ago" in ctx:
        tw = ctx["two_weeks_ago"]
        prompt += f"""
[2주 전]
- 평균 수면: {tw['avg_sleep_h']}시간 / 뒤척임: {tw['avg_restless_min']}분 / 울음: {tw['cry_count']}회
"""
    prompt += """
위 데이터를 바탕으로 3~5문장의 한국어 육아 조언을 작성하세요.
- 아기를 "아기"로 호칭 (이름 없음)
- 숫자 나열 지양, 의미 중심 해석
- 긍정적 관점 + 실용적 조언
- 의료 진단 표현 금지
- 트렌드(3주 변화)가 있으면 반드시 언급
"""
    # 기존 Gemini 호출 코드 유지
    ...
```

---

## 8. API 라우터

### 8.1 `interfaces/api/v1/report_api.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.domain.report.schemas import (
    GenerateReportRequest, GenerateReportResponse,
    ReportHistoryResponse,
)
from app.application.report import report_service

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateReportResponse,
    summary="주간 리포트 생성",
)
def generate_report(
    req: GenerateReportRequest,
    db: Session = Depends(get_db),
):
    """
    맘아이 서버가 구독 유저의 주간 데이터를 push하면 AI 리포트를 생성해 리턴.

    - sleep 배열은 반드시 7일치 (요일 순서 무관)
    - baby_name 등 개인정보 불포함 — ser_no + baby_age_months만 사용
    - 3주치 데이터가 있으면 trend 블록 포함, 없으면 null
    """
    try:
        return report_service.generate_report(db, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history/{ser_no}",
    response_model=ReportHistoryResponse,
    summary="리포트 이력 조회 (최근 3주)",
)
def get_history(
    ser_no: str,
    db: Session = Depends(get_db),
):
    """
    사용자가 앱에서 이전 리포트를 재열람할 때 호출.
    최근 3주치(최대 3개)를 최신순으로 리턴.
    """
    try:
        return report_service.get_report_history(db, ser_no)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

---

## 9. main.py 수정

```python
from app.interfaces.api.v1 import report_api

app.include_router(report_api.router, prefix="/api/v1/report", tags=["리포트"])
```

---

## 10. 스케줄러 — rolling 삭제 추가

기존 `infrastructure/scheduler.py`의 스케줄러에 아래 작업 추가:

```python
from app.infrastructure.database.repository.report_repo import delete_old_data

def _cleanup_old_data():
    """매주 월요일 리포트 생성 후 3주치 초과 데이터 삭제"""
    db = next(get_db())
    try:
        delete_old_data(db)
    finally:
        db.close()

# 기존 scheduler.add_job 아래에 추가
scheduler.add_job(
    _cleanup_old_data,
    trigger=CronTrigger(day_of_week="mon", hour=10, minute=0, timezone="Asia/Seoul"),
    id="cleanup_old_data",
)
```

---

## 11. 확정 API 목록

| 메서드 | 경로 | 호출자 | 설명 |
|--------|------|--------|------|
| `POST` | `/api/v1/report/generate` | 맘아이 서버 | 주간 데이터 push → 리포트 생성 리턴 |
| `GET`  | `/api/v1/report/history/{ser_no}` | 맘아이 앱 | 최근 3주치 리포트 이력 조회 |

---

## 12. Request / Response 예시

### POST /api/v1/report/generate

**Request:**
```json
{
  "ser_no": "MT-00123",
  "baby_age_months": 8,
  "week_start": "2026-04-07",
  "sleep": [
    { "date": "2026-04-07", "sleep_min": 570, "restless_min": 22 },
    { "date": "2026-04-08", "sleep_min": 540, "restless_min": 30 },
    { "date": "2026-04-09", "sleep_min": 600, "restless_min": 15 },
    { "date": "2026-04-10", "sleep_min": 555, "restless_min": 25 },
    { "date": "2026-04-11", "sleep_min": 510, "restless_min": 40 },
    { "date": "2026-04-12", "sleep_min": 585, "restless_min": 18 },
    { "date": "2026-04-13", "sleep_min": 560, "restless_min": 28 }
  ],
  "environment": {
    "temp_avg": 23.1, "temp_max": 24.5, "temp_min": 21.8,
    "db_max": 62, "db_avg": 48
  },
  "events": { "cry_count": 3, "leave_count": 1 }
}
```

**Response:**
```json
{
  "ser_no": "MT-00123",
  "week_start": "2026-04-07",
  "week_label": "2026년 4월 2주차",
  "generated_at": "2026-04-14T09:00:00",
  "summary": {
    "avg_sleep_h": 9.1, "avg_restless_min": 25,
    "cry_count": 3, "leave_count": 1,
    "temp_avg": 23.1, "db_max": 62
  },
  "daily": [
    { "date": "2026-04-07", "day": "월", "sleep_h": 9.5, "restless_min": 22 },
    { "date": "2026-04-08", "day": "화", "sleep_h": 9.0, "restless_min": 30 }
  ],
  "trend": {
    "sleep_vs_last_week": 0.3,
    "restless_vs_last_week": -5,
    "cry_vs_last_week": -1
  },
  "ai_comment": "이번 주 아기는 전반적으로 안정된 수면 패턴을 보였습니다. 3주 연속 울음 횟수가 줄고 수면 시간이 늘고 있어 수면 루틴이 자리잡히는 신호로 보입니다."
}
```

---

## 13. 구현 순서

```
1단계 — 데이터 레이어
  [ ] domain/report/entity.py 작성 (WeeklyData, GeneratedReport)
  [ ] domain/report/schemas.py 작성
  [ ] Alembic 마이그레이션 생성 및 적용
      → python -m alembic revision --autogenerate -m "add report tables"
      → python -m alembic upgrade head

2단계 — Repository
  [ ] infrastructure/database/repository/report_repo.py 작성
      → save_weekly_data(), get_recent_weekly_data()
      → save_report(), get_recent_reports(), delete_old_data()

3단계 — AI 클라이언트
  [ ] infrastructure/llm/gemini_client.py 수정
      → generate_insight(ctx: dict) 파라미터 구조 변경
      → 3주치 컨텍스트 포함 프롬프트로 교체

4단계 — 비즈니스 로직
  [ ] application/report/report_service.py 작성
      → generate_report()
      → get_report_history()

5단계 — API 레이어
  [ ] interfaces/api/v1/report_api.py 작성
  [ ] main.py 라우터 등록

6단계 — 스케줄러
  [ ] infrastructure/scheduler.py에 delete_old_data 작업 추가

7단계 — 검증
  [ ] uvicorn 실행 후 /docs 확인
  [ ] seed.py로 더미 데이터 삽입 후 POST /generate 호출
  [ ] 3주치 데이터 쌓은 뒤 trend 블록 정상 포함 여부 확인
  [ ] GET /history/{ser_no} 3주치 리턴 확인
  [ ] 4주 전 데이터 수동 삽입 후 rolling 삭제 확인
```

---

## 14. 주의사항 & 설계 결정

| 결정 | 이유 |
|------|------|
| `ser_no`만 식별자로 사용 | 개인정보(이름·생년월일·이메일) 보관 없음 → 개인정보처리자 의무 최소화 |
| `sleep_min` 정수로 수신 | `"9h30m"` 문자열 파싱 로직 제거, 맘아이 서버에서 변환 후 전송 |
| `baby_age_months` 맘아이 서버가 계산 | 생년월일 없이 월령 활용 가능 — AI 조언 품질 유지 |
| Weekly_Data 별도 보관 | Generated_Reports와 분리해 AI 컨텍스트(3주 트렌드) 독립 관리 |
| rolling 삭제 3주 기준 | 사용자 재열람 3주 + 여유분. 비용·개인정보 최소화 |
| upsert 방식 저장 | 동일 주차 재전송 시 중복 없이 덮어쓰기 |
| trend는 Optional | 첫 주차 사용자도 에러 없이 리포트 리턴 가능 |
