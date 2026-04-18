# M-Take 리포트 서버 — 코드베이스 심층 분석 보고서

> 작성일: 2026-04-15  
> 분석 기준: `report_server_spec.md` (확정 스펙) + 현재 코드베이스 (`feat/noh`)  
> 구현 목표 브랜치: `feat/report-server`

---

## 1. 프로젝트 개요

**프로젝트명:** M-Take 리포트 서버  
**앱 이름:** 맘아이 (mom-i)  
**역할:** 맘아이 메인 서버로부터 구독 유저의 **주간 수면 데이터를 push 받아** AI 리포트를 생성·저장·리턴하는 **전용 리포트 서버**

### 이 서버가 하는 일 (딱 3가지)

1. 맘아이 서버가 구독 유저 데이터를 **push** → AI 리포트 JSON 생성 후 즉시 리턴
2. 생성된 리포트를 **3주치** DB에 보관
3. 사용자가 앱에서 이전 리포트 **재열람** 요청 시 리턴

```
맘아이 서버 → POST /api/v1/report/generate → 리포트 JSON 리턴
앱(사용자)  → GET  /api/v1/report/history/{ser_no} → 최근 3주치 리포트 리턴
```

### 핵심 설계 원칙
- **개인정보 없음**: `baby_name`, `email`, `baby_birth` 등 일절 보관하지 않는다
- **`ser_no`(카메라 시리얼 번호)** 만 사용자 식별자로 사용
- `baby_age_months`는 맘아이 서버가 계산해서 넘겨준다 (이 서버에서 생년월일 불필요)
- 3주치 초과 데이터는 rolling 삭제 (비용·개인정보 최소화)

---

## 2. 기술 스택

| 분류 | 패키지 | 버전 | 역할 |
|------|--------|------|------|
| 웹 프레임워크 | FastAPI | 0.103.2 | REST API 서버 |
| ASGI 서버 | Uvicorn | 0.23.2 | 비동기 서버 실행 |
| 데이터 검증 | Pydantic | 2.4.2 | 요청/응답 스키마 검증 |
| 환경변수 관리 | pydantic-settings | 2.0.3 | `.env` 파일 로드 |
| ORM | SQLAlchemy | 2.0.21 | DB 추상화 레이어 |
| DB 마이그레이션 | Alembic | 1.12.1 | 스키마 버전 관리 |
| AI/LLM | google-generativeai | 0.3.1 | Gemini 1.5 Flash API |
| 스케줄링 | APScheduler | 3.10.4 | rolling 삭제 주기 실행 |
| 테스트 | pytest + httpx | 7.4.2 / 0.25.0 | 단위 및 통합 테스트 |

**프로덕션 전환 시 추가 필요:**
- `pymysql==1.1.0` — MySQL 드라이버
- `cryptography==41.0.4` — MySQL TLS 연결

---

## 3. 전체 디렉토리 구조 (확정 스펙 기준)

```
backend/app/
├── domain/report/
│   ├── __init__.py
│   ├── entity.py              ← ORM 모델 (WeeklyData, GeneratedReport)
│   └── schemas.py             ← Pydantic 요청/응답 스키마
├── application/report/
│   ├── __init__.py
│   └── report_service.py      ← 리포트 생성 비즈니스 로직
├── infrastructure/
│   ├── database/
│   │   ├── session.py         ← SQLAlchemy 세션 (기존 유지)
│   │   └── repository/
│   │       └── report_repo.py ← DB 접근 (저장, 3주치 조회, rolling 삭제)
│   ├── llm/
│   │   ├── gemini_client.py   ← Gemini API 클라이언트 (파라미터 구조 수정)
│   │   └── prompts/
│   │       └── system_prompt.md
│   └── scheduler.py           ← rolling 삭제 작업 추가
└── interfaces/api/v1/
    └── report_api.py          ← FastAPI 라우터 (POST /generate, GET /history)
```

수정 파일:
- `backend/app/main.py` — 라우터 재등록
- `backend/app/core/config.py` — 환경변수 확인

**기존 코드베이스 대비 제거되는 파일/기능:**
- `domain/sleep_data/` — 일별 수집 로직 불필요 (주간 push 방식)
- `application/sleep_data/collect_service.py`
- `interfaces/api/v1/sleep_data_api.py`
- `infrastructure/database/repository/sleep_data_repo.py`
- `infrastructure/pdf/generator.py` — JSON 리턴으로 대체
- `infrastructure/templates/` — HTML 렌더링 없음

---

## 4. 데이터베이스 스키마

**기존 코드베이스의 `Users`, `Daily_Sleep_Logs`, `Environment_Logs`, `Event_Logs` 테이블은 이 서버에 없다.**  
이 서버는 `ser_no`만으로 식별하고 아래 2개 테이블만 운영한다.

### 4.1 `Weekly_Data` — 주간 원본 데이터

AI 컨텍스트(3주 트렌드) 구성을 위해 원본 데이터를 별도 보관한다.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | Integer | PK, AutoInc | |
| `ser_no` | String(50) | NOT NULL | 기기 식별자 |
| `week_start` | Date | NOT NULL | 리포트 대상 주 시작일 (월요일) |
| `sleep_json` | JSON | NOT NULL | 7일치 수면 (`[{date, sleep_min, restless_min}, ...]`) |
| `env_json` | JSON | NOT NULL | 환경 집계 (`{temp_avg, temp_max, temp_min, db_max, db_avg}`) |
| `event_json` | JSON | NOT NULL | 이벤트 집계 (`{cry_count, leave_count}`) |
| `created_at` | TIMESTAMP | server_default=now() | |

> UNIQUE KEY (`ser_no`, `week_start`) — 동일 주차 재전송 시 upsert

### 4.2 `Generated_Reports` — 생성된 리포트

사용자 재열람 및 AI 이전 조언 참고용.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | Integer | PK, AutoInc | |
| `ser_no` | String(50) | NOT NULL | 기기 식별자 |
| `week_start` | Date | NOT NULL | 리포트 대상 주 시작일 |
| `report_json` | JSON | NOT NULL | 최종 리포트 전체 (응답 구조 그대로) |
| `ai_comment` | Text | NOT NULL | AI 조언 텍스트 |
| `created_at` | TIMESTAMP | server_default=now() | |

> UNIQUE KEY (`ser_no`, `week_start`) — 동일 주차 재전송 시 upsert

### 스키마 변경 요약 (기존 → 확정)

| | 기존 코드베이스 | 확정 스펙 |
|--|----------------|-----------|
| 사용자 식별 | `user_id` (FK → Users 테이블) | `ser_no` (String, 별도 테이블 없음) |
| 수면 저장 | `Daily_Sleep_Logs` 행 단위 | `Weekly_Data.sleep_json` (JSON) |
| 개인정보 | `email`, `baby_name`, `baby_birth` 저장 | 없음 |
| 리포트 보존 | 무기한 | 3주치 rolling 삭제 |
| 소프트 삭제 | `is_deleted` 컬럼 | 없음 (물리 삭제) |
| 리포트 저장 컬럼 | `ai_kick_comment`, `report_url` | `report_json(JSON)`, `ai_comment` |

---

## 5. API 엔드포인트

| 메서드 | 경로 | 호출자 | 설명 |
|--------|------|--------|------|
| `POST` | `/api/v1/report/generate` | 맘아이 서버 | 주간 데이터 push → AI 리포트 생성 후 즉시 리턴 |
| `GET` | `/api/v1/report/history/{ser_no}` | 맘아이 앱 | 최근 3주치 리포트 이력 조회 |

### Request 구조 (POST /generate)

```json
{
  "ser_no": "MT-00123",
  "baby_age_months": 8,
  "week_start": "2026-04-07",
  "sleep": [
    { "date": "2026-04-07", "sleep_min": 570, "restless_min": 22 },
    { "date": "2026-04-08", "sleep_min": 540, "restless_min": 30 },
    "... (반드시 7일치, validator로 강제)"
  ],
  "environment": {
    "temp_avg": 23.1, "temp_max": 24.5, "temp_min": 21.8,
    "db_max": 62, "db_avg": 48
  },
  "events": { "cry_count": 3, "leave_count": 1 }
}
```

> **수면 시간 단위 변경:** 기존 `"9h30m"` 문자열 → **`sleep_min: int`(분 단위 정수)**  
> 파싱 로직(`_parse_hours`, `_parse_minutes`) 완전 제거. 맘아이 서버에서 변환 후 전송.

### Response 구조

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
    { "date": "2026-04-07", "day": "월", "sleep_h": 9.5, "restless_min": 22 }
  ],
  "trend": {
    "sleep_vs_last_week": 0.3,
    "restless_vs_last_week": -5,
    "cry_vs_last_week": -1
  },
  "ai_comment": "이번 주 아기는 전반적으로 안정된 수면 패턴을 보였습니다..."
}
```

> `trend`는 이전 주 데이터가 없으면 `null` (첫 주차 사용자 에러 없이 처리)

---

## 6. 전체 데이터 흐름

```
맘아이 서버
  │
  └─► POST /api/v1/report/generate
        │
        ▼
      report_api.py :: generate_report()
        │
        ▼
      report_service.py :: generate_report()
        │
        ├── Step 1: report_repo.save_weekly_data()
        │     └── Weekly_Data upsert (AI 컨텍스트용 원본 보관)
        │
        ├── Step 2: 집계 계산
        │     ├── _build_summary()  → avg_sleep_h, avg_restless_min, cry/leave count
        │     ├── _build_daily()    → 7일치 DailySummary (sleep_min ÷ 60 = sleep_h)
        │     └── _build_trend()
        │           └── report_repo.get_recent_weekly_data(weeks=1)
        │                 → TrendData(sleep_vs_last_week, restless_vs_last_week, cry_vs_last_week)
        │                 → 이전 데이터 없으면 None 반환
        │
        ├── Step 3: AI 인사이트 생성
        │     ├── _build_ai_context()
        │     │     └── report_repo.get_recent_weekly_data(weeks=2)
        │     │           → this_week + last_week + two_weeks_ago 구조
        │     └── gemini_client.generate_insight(ctx)
        │           └── Gemini 1.5 Flash → 3~5문장 한국어 조언
        │
        └── Step 4: report_repo.save_report()
              └── Generated_Reports upsert
                    │
                    ▼
                  GenerateReportResponse JSON 리턴

앱(사용자)
  └─► GET /api/v1/report/history/{ser_no}
        └── report_service.get_report_history()
              └── report_repo.get_recent_reports(limit=3)
                    → week_start >= today-3주, ser_no 일치
                          ▼
                    ReportHistoryResponse(reports=[...], total=N)
```

---

## 7. 비즈니스 로직 상세

### 7.1 주차 라벨

```python
def _week_label(week_start: date) -> str:
    week_num = (week_start.day - 1) // 7 + 1
    return f"{week_start.year}년 {week_start.month}월 {week_num}주차"
```

### 7.2 요약 집계 — 파싱 로직 제거

```python
# 기존 코드 (_parse_hours, _parse_minutes) → 완전 제거
# 확정 스펙: sleep_min 정수를 60으로 나누면 끝
def _build_summary(req) -> ReportSummary:
    sleep_mins    = [s.sleep_min for s in req.sleep]
    restless_mins = [s.restless_min for s in req.sleep]
    return ReportSummary(
        avg_sleep_h=round(sum(sleep_mins) / len(sleep_mins) / 60, 1),
        avg_restless_min=round(sum(restless_mins) / len(restless_mins)),
        ...
    )
```

### 7.3 트렌드 계산

```python
def _build_trend(db, req, summary) -> Optional[TrendData]:
    prev_data = report_repo.get_recent_weekly_data(db, req.ser_no, req.week_start, weeks=1)
    if not prev_data:
        return None  # 이전 데이터 없으면 trend=null

    prev = prev_data[0]
    prev_avg_sleep_h = round(
        sum(s["sleep_min"] for s in prev.sleep_json) / 7 / 60, 1
    )
    prev_avg_restless = round(
        sum(s["restless_min"] for s in prev.sleep_json) / 7
    )
    prev_cry = prev.event_json.get("cry_count", 0)

    return TrendData(
        sleep_vs_last_week=round(summary.avg_sleep_h - prev_avg_sleep_h, 1),
        restless_vs_last_week=summary.avg_restless_min - prev_avg_restless,
        cry_vs_last_week=summary.cry_count - prev_cry,
    )
```

### 7.4 AI 컨텍스트 (최대 3주치)

```python
ctx = {
    "baby_age_months": req.baby_age_months,   # 맘아이 서버가 계산해서 넘김
    "week_label": "2026년 4월 2주차",
    "this_week":     { "avg_sleep_h": 9.1, "cry_count": 3, ... },
    "last_week":     { ... },      # 있으면 포함
    "two_weeks_ago": { ... },      # 있으면 포함
}
# → baby_name 없음, "아기"로 호칭
# → 트렌드 데이터가 있으면 프롬프트에 포함해 변화 언급 강제
```

### 7.5 Rolling 삭제

```python
def delete_old_data(db: Session) -> None:
    cutoff = date.today() - timedelta(weeks=3)
    db.query(WeeklyData).filter(WeeklyData.week_start < cutoff).delete()
    db.query(GeneratedReport).filter(GeneratedReport.week_start < cutoff).delete()
    db.commit()
# 매주 월요일 10:00 KST 스케줄러에서 자동 실행
```

---

## 8. AI 인사이트 생성 (Gemini)

**모델:** `gemini-1.5-flash`  
**기존 대비 변경점:**

| | 기존 코드베이스 | 확정 스펙 |
|--|----------------|-----------|
| 호칭 | `baby_name` 포함 ("민준이는...") | "아기" 고정 |
| 컨텍스트 | 현재 주 데이터만 | 최대 3주치 트렌드 포함 |
| 트렌드 언급 | 없음 | 3주 변화 반드시 언급하도록 프롬프트 지시 |

**프롬프트 규칙:**
- 아기를 **"아기"** 로 호칭 (이름 없음)
- 트렌드 데이터 존재 시 3주 변화 반드시 언급
- 숫자 나열 지양, 의미 중심 해석
- 의료 진단 표현 금지
- 3~5문장 한국어 서술형

---

## 9. 스케줄러

**기존 `scheduler.py`에 추가되는 작업:**

| Job ID | 실행 시각 | 역할 |
|--------|-----------|------|
| `cleanup_old_data` (신규) | 매주 월 10:00 KST | 3주치 초과 데이터 rolling 삭제 |

> 기존 `weekly_report` Job은 push 방식으로 전환되어 **제거**. 리포트 생성은 맘아이 서버가 POST로 트리거.

---

## 10. 구현 순서

```
1단계 — 데이터 레이어
  [ ] domain/report/entity.py — WeeklyData, GeneratedReport (ser_no 기반)
  [ ] domain/report/schemas.py — 전체 스키마
  [ ] Alembic 마이그레이션 생성 및 적용
      → python -m alembic revision --autogenerate -m "add report tables"
      → python -m alembic upgrade head

2단계 — Repository
  [ ] infrastructure/database/repository/report_repo.py
      → save_weekly_data(), get_recent_weekly_data()
      → save_report(), get_recent_reports(), delete_old_data()

3단계 — AI 클라이언트 수정
  [ ] infrastructure/llm/gemini_client.py
      → generate_insight(ctx: dict) 파라미터 구조 변경
      → 3주치 컨텍스트 + "아기" 호칭 프롬프트로 교체

4단계 — 비즈니스 로직
  [ ] application/report/report_service.py
      → generate_report(), get_report_history()

5단계 — API 레이어
  [ ] interfaces/api/v1/report_api.py — POST /generate, GET /history/{ser_no}
  [ ] main.py 라우터 재등록

6단계 — 스케줄러
  [ ] infrastructure/scheduler.py — cleanup_old_data 추가, weekly_report 제거

7단계 — 검증
  [ ] POST /generate 호출 → trend=null 확인 (첫 주차)
  [ ] 2~3주치 데이터 적재 후 trend 블록 정상 포함 확인
  [ ] GET /history/{ser_no} 최근 3주치 리턴 확인
  [ ] delete_old_data() 호출 후 4주 전 데이터 삭제 확인
```

---

## 11. 기존 코드베이스 vs 확정 스펙 전체 대조표

| 항목 | 기존 (`feat/noh`) | 확정 스펙 (`feat/report-server`) |
|------|-------------------|----------------------------------|
| 사용자 식별 | `Users` 테이블 + `user_id` FK | `ser_no` 문자열, 별도 테이블 없음 |
| 수면 데이터 형식 | `"9h30m"` 문자열 | `sleep_min: int` (분 단위 정수) |
| 데이터 수집 방식 | 일별 push (앱 → 서버) | 주간 push (맘아이 서버 → 리포트 서버) |
| DB 테이블 수 | 5개 | 2개 (`Weekly_Data`, `Generated_Reports`) |
| 개인정보 저장 | 이름·생년월일·이메일 | 없음 |
| AI 호칭 | `baby_name` | "아기" 고정 |
| AI 컨텍스트 | 현재 주만 | 최대 3주치 트렌드 |
| 트렌드 분석 | 없음 | `TrendData` (지난주 대비 변화) |
| 리포트 출력 | HTML + PDF | JSON 리턴만 |
| 데이터 보존 | 무기한 | 3주치 rolling 삭제 |
| 스케줄러 | 리포트 자동 생성 (pull) | rolling 삭제만 (생성은 push로 전환) |

*이 보고서는 `report_server_spec.md` 확정 스펙을 기준으로 전면 재작성되었습니다.*
