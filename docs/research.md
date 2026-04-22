# M-Take 리포트 서버 — 리포트 생성 시스템 심층 분석

> 최종 갱신: 2026-04-19  
> 분석 기준: `feat/noh` 브랜치 실제 구현 코드  
> 이전 버전(스펙 기준, 2026-04-15) → 2026-04-18 실제 코드 반영 전면 재작성  
> 2026-04-19: EMTAKE 신규 필드(breath/body_temp/monthly) 통합, 6단계 파이프라인, Gemini 2.5 Flash 업데이트

---

## 1. 프로젝트 개요

**프로젝트명:** M-Take 리포트 서버  
**앱 이름:** 맘아이 (mom-i)  
**역할:** 맘아이 메인 서버로부터 구독 유저의 **주간 수면 데이터를 push 받아** AI 리포트를 생성·저장·리턴하는 **전용 리포트 서버**

### 이 서버가 하는 일 (딱 3가지)

1. 맘아이 서버가 구독 유저 데이터를 **push** → AI 리포트 JSON 생성 후 즉시 리턴
2. 생성된 리포트와 원본 데이터를 **최대 3주치** DB에 보관
3. 사용자가 앱에서 이전 리포트 **재열람** 요청 시 리턴

```
맘아이 서버  →  POST /api/v1/report/generate   →  리포트 JSON 리턴
앱 (사용자)  →  GET  /api/v1/report/history/{ser_no}  →  최근 3주치 리포트
```

### 핵심 설계 원칙

| 원칙 | 상세 |
|------|------|
| **개인정보 없음** | `baby_name`, `email`, `baby_birth` 일절 저장 안 함 |
| **`ser_no` 단일 식별** | 카메라 시리얼 번호만 사용, Users 테이블 없음 |
| **월령 외부 계산** | `baby_age_months`는 맘아이 서버가 계산해서 넘김 |
| **rolling 삭제** | 3주치 초과 데이터 매주 자동 물리 삭제 |
| **push 방식** | 서버 자체 스케줄 생성 없음, 맘아이 서버 트리거 |

---

## 2. 기술 스택

| 분류 | 패키지 | 역할 |
|------|--------|------|
| 웹 프레임워크 | FastAPI 0.103.2 | REST API 서버 |
| ASGI 서버 | Uvicorn 0.23.2 | 비동기 서버 실행 |
| 데이터 검증 | Pydantic 2.4.2 | 요청/응답 스키마 검증 |
| 환경변수 | pydantic-settings 2.0.3 | `.env` 파일 로드 |
| ORM | SQLAlchemy 2.0.21 | DB 추상화 |
| DB 마이그레이션 | Alembic 1.12.1 | 스키마 버전 관리 |
| AI/LLM | google-generativeai 0.3.1 | Gemini 1.5 Flash API |
| 스케줄링 | APScheduler 3.10.4 | rolling 삭제 주기 실행 |
| 테스트 | pytest + httpx | 단위 및 통합 테스트 |
| DB (개발) | SQLite (`./m_take.db`) | 로컬 개발용 |
| DB (운영 예정) | MySQL + pymysql | 프로덕션 전환 시 |

---

## 3. 전체 디렉토리 구조

```
backend/app/
├── core/
│   └── config.py                         ← 환경변수 (GEMINI_API_KEY, DATABASE_URL 등)
├── domain/report/
│   ├── entity.py                         ← ORM 모델: WeeklyData, GeneratedReport
│   └── schemas.py                        ← Pydantic 스키마 (요청/응답 전체)
├── application/report/
│   └── report_service.py                 ← 비즈니스 로직 핵심 (generate_report, get_report_history)
├── infrastructure/
│   ├── database/
│   │   ├── session.py                    ← SQLAlchemy 엔진·세션·create_tables()
│   │   └── repository/
│   │       └── report_repo.py            ← DB 접근 함수 (저장, 조회, 삭제)
│   ├── llm/
│   │   ├── gemini_client.py              ← Gemini API 호출 + 프롬프트 조립
│   │   └── prompts/
│   │       └── system_prompt.md          ← Gemini 시스템 프롬프트 (역할·출력형식·규칙)
│   └── scheduler.py                      ← APScheduler: rolling 삭제 매주 월 10:00
├── interfaces/api/v1/
│   └── report_api.py                     ← FastAPI 라우터 (2개 엔드포인트)
└── main.py                               ← FastAPI 앱, CORS, 라우터 등록, 시작훅
```

---

## 4. 데이터베이스 스키마

이 서버는 테이블 **2개**만 운영한다. Users·수면 로그 등 일체 없음.

### 4.1 `Weekly_Data` — 주간 원본 데이터

**목적:** AI 컨텍스트 3주치 트렌드 구성을 위해 원본을 그대로 보관

```
entity.py:7-21
```

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | Integer | PK, AutoInc | |
| `ser_no` | String(50) | NOT NULL | 기기 시리얼 번호 |
| `week_start` | Date | NOT NULL | 주 시작일 (월요일) |
| `sleep_json` | JSON | NOT NULL | `[{date, sleep_min, restless_min}, ...]` 7일치 |
| `env_json` | JSON | NOT NULL | `{temp_avg, temp_max, temp_min, db_max, db_avg}` |
| `event_json` | JSON | NOT NULL | `{cry_count, leave_count}` |
| `breath_json` | JSON | NOT NULL | `{breath_min, breath_max, breath_avg}` 수면 중 호흡수(회/분) |
| `body_temp_json` | JSON | NOT NULL | `{body_temp_min, body_temp_max, body_temp_avg}` 수면 중 체온(°C) |
| `monthly_json` | JSON | NOT NULL | `{month_sleep_h, month_restless_h}` 월간 평균 |
| `created_at` | TIMESTAMP | server_default=now() | |

UNIQUE KEY: `(ser_no, week_start)` → 동일 주차 재전송 시 upsert (데이터 덮어쓰기)

> ⚠ **DB 재생성 필요**: SQLite는 ALTER TABLE로 JSON 컬럼 추가가 안 됨. 기존 `m_take.db` 삭제 후 재시작해야 새 컬럼이 반영된다.

### 4.2 `Generated_Reports` — 생성된 리포트

**목적:** 앱 재열람 + 향후 AI 이전 조언 참고용

```
entity.py:24-37
```

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | Integer | PK, AutoInc | |
| `ser_no` | String(50) | NOT NULL | 기기 시리얼 번호 |
| `week_start` | Date | NOT NULL | 주 시작일 (월요일) |
| `report_json` | JSON | NOT NULL | `GenerateReportResponse` 구조 그대로 |
| `ai_comment` | Text | NOT NULL | AI 조언 텍스트 (별도 추출, 빠른 접근용) |
| `created_at` | TIMESTAMP | server_default=now() | |

UNIQUE KEY: `(ser_no, week_start)` → 동일 주차 재전송 시 upsert

---

## 5. Pydantic 스키마 전체 구조

```
domain/report/schemas.py
```

### 5.1 요청 스키마 (맘아이 서버 → 리포트 서버)

```python
class SleepDay(BaseModel):
    date: date
    sleep_min: int       # 분 단위 정수 (예: 570 = 9시간 30분)
    restless_min: int    # 뒤척임 시간 (분)

class EnvironmentData(BaseModel):
    temp_avg: float
    temp_max: float
    temp_min: float
    db_max: int          # 최대 소음 (dB)
    db_avg: int          # 평균 소음 (dB)

class EventData(BaseModel):
    cry_count: int
    leave_count: int

# ── EMTAKE 신규 필드 (2026-04-19 추가) ──────────────────────────────
class BreathData(BaseModel):
    breath_min: int      # 수면 중 최소 호흡수 (회/분)
    breath_max: int      # 수면 중 최대 호흡수 (회/분)
    breath_avg: int      # 수면 중 평균 호흡수 (회/분)

class BodyTempData(BaseModel):
    body_temp_min: float # 수면 중 최저 체온 (°C)
    body_temp_max: float # 수면 중 최고 체온 (°C)
    body_temp_avg: float # 수면 중 평균 체온 (°C)

class MonthlySummary(BaseModel):
    month_sleep_h: float    # 이번 달 평균 수면 시간 (시간)
    month_restless_h: float # 이번 달 평균 뒤척임 시간 (시간)

class GenerateReportRequest(BaseModel):
    ser_no: str              # 기기 식별자
    baby_age_months: int     # 맘아이 서버가 계산해서 넘김
    week_start: date         # 월요일
    sleep: List[SleepDay]   # 반드시 7일치 (validator 강제)
    environment: EnvironmentData
    events: EventData
    breath: BreathData           # EMTAKE CMD:Breath
    body_temp: BodyTempData      # EMTAKE CMD:Temp
    monthly: MonthlySummary      # EMTAKE CMD:SleepData month_gs/month_pr

    @field_validator("sleep")
    @classmethod
    def sleep_must_be_7_days(cls, v):
        if len(v) != 7:
            raise ValueError(f"sleep 데이터는 7일치여야 합니다 (현재: {len(v)}일)")
        return v
```

> 핵심: `sleep_min`은 문자열이 아닌 **정수**. `"9h30m"` 같은 파싱 로직 없음.  
> 맘아이 서버가 분 단위로 변환 후 전송해야 한다.  
> `breath`, `body_temp`, `monthly`는 EMTAKE 프로토콜 CMD 데이터를 집계해서 전송.

### 5.2 응답 스키마 (리포트 서버 → 맘아이 서버)

```python
class DailySummary(BaseModel):
    date: date
    day: str           # "월", "화", "수", "목", "금", "토", "일"
    sleep_h: float     # sleep_min / 60, 소수점 1자리
    restless_min: int

class TrendData(BaseModel):
    sleep_vs_last_week: float        # 양수: 증가, 음수: 감소 (시간 단위)
    restless_vs_last_week: int       # 양수: 증가, 음수: 감소 (분 단위)
    cry_vs_last_week: int
    breath_vs_last_week: int         # 호흡수 변화 (회/분)
    body_temp_vs_last_week: float    # 체온 변화 (°C)

class ReportSummary(BaseModel):
    avg_sleep_h: float
    avg_restless_min: int
    cry_count: int
    leave_count: int
    temp_avg: float
    db_max: int
    month_sleep_h: float        # 월간 평균 수면 (monthly에서)
    month_restless_h: float     # 월간 평균 뒤척임 (monthly에서)

# ── 호흡수 분석 결과 (응답 포함) ─────────────────────────────────────
class BreathSummary(BaseModel):
    breath_min: int
    breath_max: int
    breath_avg: int
    is_normal: bool      # AAP 기준 월령별 정상 범위 여부
    normal_range: str    # "20~40회/분 (생후 12개월 이하 기준)"

# ── 체온 분석 결과 (응답 포함) ───────────────────────────────────────
class BodyTempSummary(BaseModel):
    body_temp_min: float
    body_temp_max: float
    body_temp_avg: float
    status: str          # "정상" | "미열 주의" | "발열 의심"

class GenerateReportResponse(BaseModel):
    ser_no: str
    week_start: date
    week_label: str        # "2026년 4월 2주차"
    generated_at: datetime
    summary: ReportSummary
    breath: BreathSummary          # 호흡수 분석 결과
    body_temp: BodyTempSummary     # 체온 분석 결과
    daily: List[DailySummary]      # 7개 고정
    trend: Optional[TrendData]     # 이전 데이터 없으면 None
    ai_comment: str
```

### 5.3 이력 조회 스키마 (앱 → 리포트 서버)

```python
class ReportItem(BaseModel):
    week_start: date
    week_label: str
    report_json: Dict[str, Any]   # GenerateReportResponse 구조 그대로

class ReportHistoryResponse(BaseModel):
    reports: List[ReportItem]
    total: int
```

---

## 6. API 엔드포인트

```
interfaces/api/v1/report_api.py
main.py  →  prefix="/api/v1/report"
```

### 6.1 `POST /api/v1/report/generate` — 주간 리포트 생성

- **호출자:** 맘아이 서버 (구독 유저 주간 데이터 push)
- **Response model:** `GenerateReportResponse`
- **에러 처리:** 모든 예외 → `HTTP 500` + `detail: str(e)`

```
report_api.py:15-34
```

### 6.2 `GET /api/v1/report/history/{ser_no}` — 이력 조회

- **호출자:** 맘아이 앱 (사용자 재열람 요청)
- **Response model:** `ReportHistoryResponse`
- **에러 처리:** 리포트 없을 시 `ValueError` → `HTTP 404`
- **반환 범위:** 최신순, 최대 3개, `week_start >= 오늘 - 3주`

```
report_api.py:37-53
```

### 6.3 요청/응답 예시

**요청 (POST /generate):**
```json
{
  "ser_no": "MT-00123",
  "baby_age_months": 8,
  "week_start": "2026-04-07",
  "sleep": [
    { "date": "2026-04-07", "sleep_min": 570, "restless_min": 22 },
    { "date": "2026-04-08", "sleep_min": 540, "restless_min": 30 },
    { "date": "2026-04-09", "sleep_min": 600, "restless_min": 15 },
    { "date": "2026-04-10", "sleep_min": 555, "restless_min": 28 },
    { "date": "2026-04-11", "sleep_min": 510, "restless_min": 35 },
    { "date": "2026-04-12", "sleep_min": 590, "restless_min": 18 },
    { "date": "2026-04-13", "sleep_min": 620, "restless_min": 12 }
  ],
  "environment": {
    "temp_avg": 23.1, "temp_max": 24.5, "temp_min": 21.8,
    "db_max": 62, "db_avg": 48
  },
  "events": { "cry_count": 3, "leave_count": 1 },
  "breath": { "breath_min": 22, "breath_max": 38, "breath_avg": 28 },
  "body_temp": { "body_temp_min": 36.3, "body_temp_max": 37.1, "body_temp_avg": 36.7 },
  "monthly": { "month_sleep_h": 9.2, "month_restless_h": 0.5 }
}
```

**응답:**
```json
{
  "ser_no": "MT-00123",
  "week_start": "2026-04-07",
  "week_label": "2026년 4월 2주차",
  "generated_at": "2026-04-14T09:00:00",
  "summary": {
    "avg_sleep_h": 9.3,
    "avg_restless_min": 23,
    "cry_count": 3,
    "leave_count": 1,
    "temp_avg": 23.1,
    "db_max": 62,
    "month_sleep_h": 9.2,
    "month_restless_h": 0.5
  },
  "breath": {
    "breath_min": 22,
    "breath_max": 38,
    "breath_avg": 28,
    "is_normal": true,
    "normal_range": "20~40회/분 (생후 12개월 이하 기준)"
  },
  "body_temp": {
    "body_temp_min": 36.3,
    "body_temp_max": 37.1,
    "body_temp_avg": 36.7,
    "status": "정상"
  },
  "daily": [
    { "date": "2026-04-07", "day": "월", "sleep_h": 9.5, "restless_min": 22 },
    "... (7개)"
  ],
  "trend": {
    "sleep_vs_last_week": 0.3,
    "restless_vs_last_week": -5,
    "cry_vs_last_week": -1,
    "breath_vs_last_week": 2,
    "body_temp_vs_last_week": -0.1
  },
  "ai_comment": "### 이번 주 총평\n이번 주 아기는 ...\n\n### 수면 패턴 분석\n...\n\n### 호흡 및 체온 분석\n...\n\n### 환경 영향 분석\n...\n\n### 부모 조언\n..."
}
```

> `trend`는 이전 주 데이터가 없으면 `null`. 첫 주차 에러 없이 정상 처리됨.

---

## 7. 전체 데이터 흐름 (실행 순서 상세)

```
맘아이 서버
  │
  └─► POST /api/v1/report/generate  (GenerateReportRequest)
        │
        ▼  report_api.py :: generate_report()
        │  └── report_service.generate_report(db, req) 호출
        │
        ▼  Step 1 — 원본 데이터 저장
        │  report_repo.save_weekly_data(db, ser_no, week_start,
        │      sleep_json, env_json, event_json,
        │      breath_json, body_temp_json, monthly_json   ← 2026-04-19 추가
        │  )
        │  → Weekly_Data upsert (ser_no + week_start 기준)
        │  → 재전송 시에도 항상 최신 원본 보존 (다음 주 트렌드 컨텍스트 정확성)
        │
        ▼  Step 2 — 캐시 확인 (Gemini 비용 절감)  ← 2026-04-19 추가
        │  report_repo.get_existing_report(db, ser_no, week_start)
        │  → 동일 주차 리포트 있으면 즉시 반환 (Gemini 재호출 없음)
        │  → 없으면 Step 3으로 진행
        │
        ▼  Step 3 — 이전 데이터 조회 (1회, 이후 재사용)  ← 2026-04-19 최적화
        │  prev_data = get_recent_weekly_data(db, ser_no, week_start, weeks=2)
        │  → _build_trend()와 _build_ai_context() 모두 이 결과 재사용
        │  → DB 쿼리 중복 완전 제거
        │
        ▼  Step 4 — 집계 계산
        │
        ├── _build_summary(req)
        │     avg_sleep_h / avg_restless_min / cry_count / leave_count
        │     month_sleep_h / month_restless_h  ← monthly에서
        │     → ReportSummary 반환
        │
        ├── _build_daily(req)
        │     date.weekday() → _DAY_KO / sleep_h = round(sleep_min / 60, 1)
        │     → List[DailySummary] 7개 반환
        │
        ├── _build_breath_summary(req)  ← 2026-04-19 추가
        │     AAP 기준 월령별 정상 범위 조회 → is_normal 판정
        │     → BreathSummary 반환
        │
        ├── _build_body_temp_summary(req)  ← 2026-04-19 추가
        │     body_temp_max 기준 판정: 정상/미열주의/발열의심
        │     → BodyTempSummary 반환
        │
        └── _build_trend(prev_data, summary, req)
              prev_data[0] = 직전 주 (없으면 None 반환)
              5개 지표 차이값 계산:
                sleep/restless/cry + breath_avg + body_temp_avg  ← 2026-04-19 추가
              → TrendData 반환
        │
        ▼  Step 5 — AI 컨텍스트 구성 + Gemini 비동기 호출  ← 2026-04-19 async 전환
        │
        ├── _build_ai_context(req, summary, breath_summary, body_temp_summary, prev_data)
        │     this_week: 수면/환경/호흡수/체온/월간 전체  ← 2026-04-19 호흡·체온 추가
        │     daily: 7일치 일별 데이터
        │     last_week / two_weeks_ago: prev_data 재사용 (추가 쿼리 없음)
        │
        └── await gemini_client.generate_insight(ctx)  ← 2026-04-19 async
              → 재시도 최대 3회 (지수 백오프 1s→2s→4s)
              → 5섹션 검증 (누락 시 보정 재호출)
              → 토큰 사용량 로깅
              → Thinking Budget 1024 토큰
        │
        ▼  Step 6 — 리포트 저장 및 반환  ← (구 Step 4)
        │  GenerateReportResponse 생성 (breath/body_temp 필드 포함)
        │  report_repo.save_report() → Generated_Reports upsert
        │
        ▼  GenerateReportResponse JSON 리턴

앱 (사용자)
  └─► GET /api/v1/report/history/{ser_no}
        └── report_service.get_report_history(db, ser_no)  [report_service.py:184-198]
              report_repo.get_recent_reports(db, ser_no, limit=3)
              → cutoff = date.today() - 3주
              → week_start >= cutoff AND ser_no 일치
              → 최신순 정렬, 최대 3개
              reports 없으면 ValueError → HTTP 404
              → ReportHistoryResponse(reports=[ReportItem, ...], total=N)
```

---

## 8. Repository 함수 상세

```
infrastructure/database/repository/report_repo.py
```

### 8.0 `get_existing_report()` — 캐시 확인 (2026-04-19 추가)

```python
def get_existing_report(db, ser_no, week_start) -> GeneratedReport | None:
    return db.query(GeneratedReport).filter(
        and_(GeneratedReport.ser_no == ser_no, GeneratedReport.week_start == week_start)
    ).first()
```

동일 `(ser_no, week_start)` 리포트가 이미 있으면 None이 아닌 객체를 반환.  
`generate_report()`에서 Step 1 이후 즉시 호출해 Gemini 재호출을 차단한다.

---

### 8.1 `save_weekly_data()` — Weekly_Data upsert

```python
def save_weekly_data(
    db, ser_no, week_start,
    sleep_json, env_json, event_json,
    breath_json, body_temp_json, monthly_json,   # 2026-04-19 추가
) -> WeeklyData:
    existing = db.query(WeeklyData).filter(
        and_(WeeklyData.ser_no == ser_no, WeeklyData.week_start == week_start)
    ).first()

    if existing:       # 같은 주차 재전송 → 덮어쓰기
        existing.sleep_json = sleep_json
        existing.env_json   = env_json
        existing.event_json = event_json
    else:              # 신규
        existing = WeeklyData(ser_no=ser_no, week_start=week_start, ...)
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing
```

### 8.2 `get_recent_weekly_data()` — AI 컨텍스트 조회

```python
def get_recent_weekly_data(db, ser_no, week_start, weeks=2) -> List[WeeklyData]:
    cutoff = week_start - timedelta(weeks=weeks)
    return (
        db.query(WeeklyData)
        .filter(
            WeeklyData.ser_no == ser_no,
            WeeklyData.week_start >= cutoff,    # cutoff 이후
            WeeklyData.week_start < week_start, # 이번 주 제외
        )
        .order_by(WeeklyData.week_start.desc()) # 최신 순
        .all()
    )
```

**호출 케이스 (2026-04-19 최적화 후):**
- `weeks=2` → `generate_report()` 내부에서 1회만 호출
- `_build_trend()`와 `_build_ai_context()` 모두 이 결과를 파라미터로 받아 재사용
- DB 쿼리 중복 완전 제거 (구버전은 2회 별도 호출)

### 8.3 `save_report()` — Generated_Reports upsert

```python
def save_report(db, ser_no, week_start, report_json, ai_comment) -> GeneratedReport:
    existing = db.query(GeneratedReport).filter(
        and_(GeneratedReport.ser_no == ser_no, GeneratedReport.week_start == week_start)
    ).first()

    if existing:
        existing.report_json = report_json
        existing.ai_comment  = ai_comment
    else:
        existing = GeneratedReport(ser_no=ser_no, week_start=week_start, ...)
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing
```

### 8.4 `get_recent_reports()` — 앱 재열람용

```python
def get_recent_reports(db, ser_no, limit=3) -> List[GeneratedReport]:
    cutoff = date.today() - timedelta(weeks=3)
    return (
        db.query(GeneratedReport)
        .filter(
            GeneratedReport.ser_no == ser_no,
            GeneratedReport.week_start >= cutoff,
        )
        .order_by(GeneratedReport.week_start.desc())
        .limit(limit)
        .all()
    )
```

### 8.5 `delete_old_data()` — Rolling 삭제

```python
def delete_old_data(db: Session) -> None:
    cutoff = date.today() - timedelta(weeks=3)
    db.query(WeeklyData).filter(WeeklyData.week_start < cutoff).delete()
    db.query(GeneratedReport).filter(GeneratedReport.week_start < cutoff).delete()
    db.commit()
```

**삭제 기준:** `week_start < (오늘 - 3주)` → 3주보다 오래된 데이터 완전 물리 삭제  
**실행 시점:** 매주 월요일 10:00 KST (scheduler.py)

---

## 9. 비즈니스 로직 상세

### 9.1 주차 라벨 생성

```python
# report_service.py:20-23
def _week_label(week_start: date) -> str:
    week_num = (week_start.day - 1) // 7 + 1
    return f"{week_start.year}년 {week_start.month}월 {week_num}주차"
```

**예시:**

| week_start | day | (day-1)//7+1 | 결과 |
|------------|-----|---------------|------|
| 2026-04-07 | 7   | (6)//7+1 = 1  | 2026년 4월 1주차 |
| 2026-04-14 | 14  | (13)//7+1 = 2 | 2026년 4월 2주차 |
| 2026-04-21 | 21  | (20)//7+1 = 3 | 2026년 4월 3주차 |
| 2026-04-28 | 28  | (27)//7+1 = 4 | 2026년 4월 4주차 |

### 9.2 요일 한글 변환

```python
_DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]
# date.weekday() → 0=월요일, 6=일요일
day = _DAY_KO[s.date.weekday()]
```

### 9.3 수면 시간 집계

```python
# sleep_min (분 정수) → 시간 (소수점 1자리)
avg_sleep_h = round(sum(sleep_mins) / len(sleep_mins) / 60, 1)

# 예: [570, 540, 600, 555, 510, 590, 620]
# sum = 3985, avg = 569.3, / 60 = 9.49 → round = 9.5
```

### 9.4 트렌드 계산 방향

```
양수(+) = 이번 주가 더 많음/더 길었음
음수(-) = 이번 주가 더 적음/더 짧았음

sleep_vs_last_week    = 이번주 avg_sleep_h - 지난주 avg_sleep_h
restless_vs_last_week = 이번주 avg_restless_min - 지난주 avg_restless_min
cry_vs_last_week      = 이번주 cry_count - 지난주 cry_count
```

### 9.5 DB 쿼리 최적화 (2026-04-19 개선)

구버전은 `get_recent_weekly_data`를 두 번 호출했으나, 현재는 1회로 통합됨:

```python
# generate_report() 내부 — 1회만 조회
prev_data = report_repo.get_recent_weekly_data(db, req.ser_no, req.week_start, weeks=2)

# 두 함수 모두 prev_data를 파라미터로 받아 재사용 (추가 DB 호출 없음)
trend          = _build_trend(prev_data, summary, req)
ai_context     = _build_ai_context(req, summary, breath_summary, body_temp_summary, prev_data)
```

---

## 10. Gemini AI 인사이트 생성 상세

```
infrastructure/llm/gemini_client.py
infrastructure/llm/prompts/system_prompt.md
```

### 10.1 모델 초기화

```python
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

_SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system_prompt.md"

_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",   # 2026-04-19: 1.5 → 2.5 업그레이드
    system_instruction=_SYSTEM_PROMPT.read_text(encoding="utf-8"),
)
```

모델 인스턴스는 **모듈 레벨에서 한 번만 초기화** (`_model`). 요청마다 재생성 없음.

**Gemini 2.5 Flash 선택 근거:**
- 1.5 Flash 대비 수치 추론 품질 향상 (호흡수·체온 기준값 판정)
- Thinking budget 파라미터 공식 지원 (`thinking_config`)
- 응답 속도 유지하면서 추론 깊이 제어 가능

### 10.2 시스템 프롬프트 (`system_prompt.md`)

Gemini에 고정으로 주입되는 역할·형식·규칙:

```
역할: 영유아 수면 전문 분석가
      맘아이 스마트 카메라 수집 주간 데이터 기반 리포트 작성

출력 형식: 반드시 5개 섹션 순서대로  ← 2026-04-19: 4→5 섹션 확장
  ### 이번 주 총평
  ### 수면 패턴 분석
  ### 호흡 및 체온 분석   ← 신규 추가
  ### 환경 영향 분석
  ### 부모 조언

규칙:
  - 아기를 반드시 "아기"로만 호칭
  - 수치 나열 지양, 의미 해석 전달
  - 긍정적 관찰 + 실용적 팁 위주
  - 의학적 진단 표현 절대 금지
  - 트렌드 데이터 있으면 반드시 변화 방향 언급
  - 분량: A4 한 장 기준 (약 500~700자)
  - 출력 언어: 한국어

기준값 (2026-04-19 도메인 지식 반영 완료):
  - 월령별 권장 수면 시간 (AAP)
  - 월령별 정상 호흡수 범위 (AAP)
  - 체온 판정 기준 (정상/미열주의/발열의심)
  - 뒤척임 임계값 (30분 미만 정상, 30~60분 주의, 60분 이상 개선필요)
  - 실내 환경 권장 기준 (18~22°C, 50dB 이하)
```

> **2026-04-19 업데이트:** 시스템 프롬프트에 모든 도메인 기준값이 명시됨.  
> 이전에 "(도메인 전문가 작성 예정)" 플레이스홀더였던 부분이 AAP/임상 기준으로 채워짐.

### 10.3 신뢰성 장치 (2026-04-19 추가)

```python
# ① 비동기 호출 — Gemini 응답 대기(3~8초) 동안 이벤트 루프 non-blocking
async def generate_insight(ctx: dict) -> str:
    result = await _call_gemini(prompt)

# ② 지수 백오프 재시도 (최대 3회, 1s→2s→4s)
for attempt in range(1, 4):
    try:
        response = await _model.generate_content_async(prompt, generation_config=...)
        return response.text.strip()
    except Exception as exc:
        if _is_retryable(exc):   # "429", "503" 등
            await asyncio.sleep(1.0 * 2**(attempt-1))

# ③ 5섹션 출력 검증
missing = [s for s in _REQUIRED_SECTIONS if s not in result]
if missing:
    result = await _call_gemini(prompt + f"\n\n누락된 섹션:\n" + "\n".join(missing))

# ④ 토큰 사용량 로깅
logger.info("[Gemini 토큰] 입력: %d / 출력: %d / 합계: %d",
    meta.prompt_token_count, meta.candidates_token_count, meta.total_token_count)

# ⑤ Thinking Budget — 수치 추론 품질 유지
generation_config = {"thinking_config": {"thinking_budget": 1024}}
```

### 10.4 사용자 프롬프트 조립 (`_build_prompt`)

```python
def _build_prompt(ctx: dict) -> str:
    tw = ctx["this_week"]

    # ① 일별 수면 텍스트 생성
    day_lines = "\n".join(
        f"  {d['day']}: 수면 {d['sleep_h']}h / 뒤척임 {d['restless_min']}분"
        for d in ctx.get("daily", [])
    )

    # ② 기본 프롬프트 (항상 포함)
    prompt = f"""
생후 {ctx['baby_age_months']}개월 아기의 {ctx['week_label']} 수면 데이터입니다.

[주간 요약]
- 평균 수면: {tw['avg_sleep_h']}시간 / 평균 뒤척임: {tw['avg_restless_min']}분
- 울음: {tw['cry_count']}회 / 카메라 이탈: {tw['leave_count']}회
- 온도: 평균 {tw['temp_avg']}°C (최고 {tw['temp_max']}° / 최저 {tw['temp_min']}°)
- 소음: 평균 {tw['db_avg']}dB / 최대 {tw['db_max']}dB

[일별 수면]
{day_lines}
"""

    # ③ 지난 주 비교 (last_week 있을 때만 추가)
    if "last_week" in ctx:
        lw = ctx["last_week"]
        prompt += f"""
[지난 주 대비]
- 수면: {lw['avg_sleep_h']}h → {tw['avg_sleep_h']}h
- 뒤척임: {lw['avg_restless_min']}분 → {tw['avg_restless_min']}분
- 울음: {lw['cry_count']}회 → {tw['cry_count']}회
"""

    # ④ 2주 전 (two_weeks_ago 있을 때만 추가)
    if "two_weeks_ago" in ctx:
        ww = ctx["two_weeks_ago"]
        prompt += f"""
[2주 전]
- 수면 {ww['avg_sleep_h']}h / 뒤척임 {ww['avg_restless_min']}분 / 울음 {ww['cry_count']}회
"""

    # ⑤ 출력 지시
    prompt += """
위 데이터를 바탕으로 시스템 프롬프트에 정의된 4개 섹션
(### 이번 주 총평 / ### 수면 패턴 분석 / ### 환경 영향 분석 / ### 부모 조언)을 순서대로 작성하라.
"""

    response = _model.generate_content(prompt)
    return response.text.strip()
```

### 10.4 AI 컨텍스트 누적 시나리오

| 이번 주 요청 시 DB 상태 | 프롬프트 포함 섹션 |
|------------------------|-------------------|
| 이전 데이터 없음 (첫 주차) | `[주간 요약]` + `[일별 수면]`만 |
| 1주 전 데이터 있음 | + `[지난 주 대비]` 추가 |
| 2주 전 데이터도 있음 | + `[2주 전]` 추가 |

### 10.5 AI 컨텍스트와 트렌드 계산의 차이

| 구분 | 목적 | DB 조회 | 반환 |
|------|------|---------|------|
| `_build_trend()` | 응답 JSON의 `trend` 필드 | `weeks=1` | `TrendData` 또는 `None` |
| `_build_ai_context()` | Gemini 프롬프트 데이터 | `weeks=2` | `dict` (ctx) |

두 함수 모두 `get_recent_weekly_data()` 를 호출하지만 **목적이 다르고 DB 쿼리를 별도로 실행**한다.

---

## 11. 스케줄러

```
infrastructure/scheduler.py
```

```python
_scheduler = BackgroundScheduler(timezone="Asia/Seoul")

def _cleanup_old_data():
    # 순환 참조 방지를 위해 함수 내부에서 import
    from app.infrastructure.database.session import SessionLocal
    from app.infrastructure.database.repository.report_repo import delete_old_data
    db = SessionLocal()
    try:
        delete_old_data(db)   # WeeklyData + GeneratedReport 동시 삭제
        logger.info("[스케줄러] 오래된 데이터 삭제 완료 (3주 초과)")
    except Exception as e:
        logger.error(f"[스케줄러] 데이터 삭제 실패: {e}")
    finally:
        db.close()

def start_scheduler():
    _scheduler.add_job(
        _cleanup_old_data,
        trigger=CronTrigger(day_of_week="mon", hour=10, minute=0),
        id="cleanup_old_data",
        replace_existing=True,
    )
    _scheduler.start()
```

- **실행 주기:** 매주 월요일 10:00 KST
- **삭제 대상:** `week_start < 오늘 - 3주` 인 모든 행 (물리 삭제, 소프트 삭제 없음)
- `start_scheduler()`는 `main.py`의 `@app.on_event("startup")` 훅에서 호출됨

---

## 12. 앱 시작 흐름 (`main.py`)

```python
app = FastAPI(
    title="M-Take 리포트 서버",
    version="0.2.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)  # 운영 시 교체 필요

@app.on_event("startup")
def on_startup():
    create_tables()       # SQLAlchemy Base.metadata.create_all() — 테이블 없으면 생성
    start_scheduler()     # APScheduler 시작

app.include_router(report_api.router, prefix="/api/v1/report", tags=["리포트"])
app.include_router(etf_api.router,    prefix="/api/v1/etf",    tags=["ETF 리밸런싱"])

@app.get("/")
async def root():
    return {"message": "M-Take 리포트 서버"}
```

---

## 13. 환경변수 (`core/config.py`)

```python
class Settings(BaseSettings):
    PROJECT_NAME: str = "M-Take 리포트 서버"
    GEMINI_API_KEY: str = ""          # 필수 — 없으면 Gemini 호출 실패
    DATABASE_URL: str = "sqlite:///./m_take.db"   # 개발용 SQLite
    MARKET_API_URL: str = ""          # ETF 기능용 (리포트 서버와 무관)
    MARKET_API_KEY: str = ""          # ETF 기능용 (리포트 서버와 무관)

    class Config:
        env_file = ".env"
```

**운영 전환 시 필수 변경:**
- `DATABASE_URL` → MySQL 연결 문자열 (`mysql+pymysql://...`)
- `GEMINI_API_KEY` → Google AI Studio에서 발급
- `CORS allow_origins` → 실제 맘아이 앱 도메인

---

## 14. 테스트 시뮬레이터

```
application/sleep_data/simulator_service.py
```

실제 맘아이 서버가 보내는 것과 동일한 구조의 더미 데이터 생성기.

```python
def make_dummy_week(ser_no="MT-00123", baby_age_months=8, week_start=None) -> dict:
    """GenerateReportRequest 와 동일한 구조 반환"""
    # sleep_min: random.randint(480, 620)  → 8h~10h20m
    # restless_min: random.randint(5, 40)
    # temp_avg: random.uniform(21.0, 24.0)
    # db_max: random.randint(50, 70)
    # cry_count: random.randint(0, 5)
    # leave_count: random.randint(0, 2)

def make_multi_week_dummy(ser_no="MT-00123", baby_age_months=8, num_weeks=3) -> list[dict]:
    """N주치 더미 데이터 리스트 반환 (최신 → 과거 순 생성 후 과거→최신 순 반환)"""
    # POST /generate를 여러 번 호출하는 3주치 트렌드 시나리오 테스트에 활용
```

---

## 15. 에러 처리 요약

| 상황 | 발생 위치 | 처리 방식 |
|------|-----------|-----------|
| sleep 배열이 7개 아님 | Pydantic validator | `HTTP 422 Unprocessable Entity` (자동) |
| Gemini API 실패 | `generate_insight()` | 예외 전파 → `HTTP 500` |
| DB 저장 실패 | `report_repo.*` | 예외 전파 → `HTTP 500` |
| 이력 조회 결과 없음 | `get_report_history()` | `ValueError` → `HTTP 404` |
| 동일 주차 재전송 | `save_weekly_data()` / `save_report()` | upsert (정상 처리) |
| 첫 주차 (이전 데이터 없음) | `_build_trend()` | `trend: null` 정상 반환 |

---

## 16. 현재 구현 상태 vs 미완성 사항

### 완성된 기능

- [x] `POST /generate` — 리포트 생성 전체 흐름
- [x] `GET /history/{ser_no}` — 이력 조회
- [x] `Weekly_Data` upsert + 3주 트렌드 컨텍스트
- [x] `TrendData` 자동 계산
- [x] Gemini 4개 섹션 포맷 프롬프트
- [x] Rolling 삭제 스케줄러
- [x] 시뮬레이터 더미 데이터 생성기

### 미완성 / 개선 필요 사항

- [ ] **시스템 프롬프트 도메인 내용 미완성** — 섹션 기준(월령별 권장 수면시간, 뒤척임 임계값 등)이 "(도메인 전문가 작성 예정)" 상태
- [ ] **DB 쿼리 중복** — `_build_trend(weeks=1)`과 `_build_ai_context(weeks=2)` 가 별도 쿼리 2회 실행 → `weeks=2` 1회로 통합 가능
- [ ] **인증/인가 없음** — `POST /generate` 엔드포인트에 맘아이 서버 전용 API 키 검증 없음
- [ ] **PDF 출력 미연결** — `infrastructure/pdf/generator.py`는 존재하지만 라우터에 등록 안 됨
- [ ] **Alembic 마이그레이션 미적용** — `create_tables()`로 런타임 생성 중, 운영 전 마이그레이션 필요
- [ ] **CORS 와일드카드** — `allow_origins=["*"]` → 운영 시 실제 도메인으로 교체 필요
- [ ] **에러 로깅** — Gemini 호출 실패 등 주요 에러에 대한 구조화 로깅 없음

---

## 17. 전체 레이어 의존 관계

```
[HTTP 요청]
    │
    ▼
interfaces/api/v1/report_api.py   ← FastAPI 라우터, HTTP 변환, 에러 핸들링
    │
    ▼
application/report/report_service.py  ← 비즈니스 로직 (집계, 트렌드, AI 호출 조율)
    │
    ├── infrastructure/database/repository/report_repo.py  ← DB CRUD
    │       └── domain/report/entity.py  ← SQLAlchemy ORM 모델
    │
    └── infrastructure/llm/gemini_client.py  ← Gemini API 호출
            └── prompts/system_prompt.md  ← 시스템 프롬프트

domain/report/schemas.py  ← 모든 레이어가 참조하는 Pydantic 스키마
core/config.py            ← 환경변수, 전 레이어에서 import
```

각 레이어는 아래 방향으로만 의존하며 역방향 의존 없음.
