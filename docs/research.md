# 맘아이 리포트 서버 — 시스템 분석

> 최종 갱신: 2026-04-27  
> 기준: `feat/noh` 실제 구현 코드

---

## 1. 역할

맘아이 메인 서버로부터 주간 수면 데이터를 push 받아 Gemini AI로 분석한 후 리포트 JSON을 생성·저장·제공하는 **리포트 전담 마이크로서비스**.

```
맘아이 서버  →  POST /api/v1/reports/generate   →  리포트 JSON 반환
앱 (사용자)  →  GET  /api/v1/reports             →  목록 (최근 10건)
앱 (사용자)  →  GET  /api/v1/reports/{id}        →  상세
관리자       →  GET  /api/v1/admin/*             →  통계·기기 조회
```

**핵심 원칙:** JWT 발급 없음, 개인정보 없음(`ser_no`만 식별자), push 방식(서버 자체 스케줄 생성 없음)

---

## 2. 기술 스택

| 분류 | 기술 |
|------|------|
| 프레임워크 | FastAPI 0.135.3 + Uvicorn 0.44.0 |
| ORM / DB | SQLAlchemy 2.0.49 + MariaDB 10.11 (Docker) |
| AI | google-genai (Gemini 3 Flash Preview) |
| 인증 | python-jose (JWT HS256 검증) |
| 스케줄러 | APScheduler 3.11.2 |

---

## 3. 디렉토리 구조

```
backend/app/
├── core/
│   ├── config.py          ← 환경변수 (루트 .env 로드)
│   └── security.py        ← JWT 검증 / API Key 검증
├── domain/report/
│   ├── entity.py          ← WeeklyData, GeneratedReport ORM
│   └── schemas.py         ← 요청/응답 Pydantic 스키마 전체
├── application/report/
│   └── report_service.py  ← 비즈니스 로직 (6단계 파이프라인)
├── infrastructure/
│   ├── database/
│   │   ├── session.py
│   │   └── repository/report_repo.py
│   ├── llm/
│   │   ├── gemini_client.py
│   │   └── prompts/       ← system·knowledge·age_policy·reasoning·output_format·input_template
│   └── scheduler.py
└── interfaces/api/v1/
    ├── report_api.py
    └── admin_api.py
```

---

## 4. DB 스키마

### Weekly_Data

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer PK | |
| ser_no | String(50) | 기기 시리얼 번호 |
| week_start | Date | 주 시작일 (월요일) |
| sleep_json | JSON | `[{date, sleep_min, restless_min}]` 7일치 |
| env_json | JSON | `{temp_avg, temp_max, temp_min, db_max, db_avg}` |
| event_json | JSON | `{cry_count, leave_count}` |
| breath_json | JSON | `{breath_min, breath_max, breath_avg}` |
| body_temp_json | JSON | `{body_temp_min, body_temp_max, body_temp_avg}` |
| monthly_json | JSON | `{month_sleep_h, month_restless_h}` |
| created_at | TIMESTAMP | |

UNIQUE KEY: `(ser_no, week_start)`

### Generated_Reports

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer PK | |
| ser_no | String(50) | |
| week_start | Date | |
| report_json | JSON | GenerateReportResponse 구조 전체 |
| ai_comment | Text | ai_comment 빠른 접근용 |
| created_at | TIMESTAMP | |

UNIQUE KEY: `(ser_no, week_start)`

---

## 5. 리포트 생성 파이프라인 (6단계)

```
POST /api/v1/reports/generate
  │
  ├─ 1. Weekly_Data UPSERT          ← 항상 최신 원본 저장
  ├─ 2. Generated_Reports 캐시 확인 ← HIT 시 Gemini 재호출 없이 즉시 반환
  ├─ 3. 이전 2주치 조회 (1회)       ← trend + AI context 공용
  ├─ 4. 집계
  │     ├─ summary  (avg_sleep_h, avg_restless_min, cry_count, ...)
  │     ├─ daily    (요일별 sleep_h, restless_min)
  │     ├─ breath   (breath_avg, is_normal, normal_range)
  │     ├─ body_temp(body_temp_avg, status: 정상/미열주의/발열의심)
  │     └─ trend    (전주 대비 수면·뒤척임·울음·호흡·체온 차이)
  ├─ 5. gemini_client.generate_insight()
  │     ├─ 최대 3회 재시도
  │     ├─ response_mime_type: application/json 강제
  │     └─ _validate_json() → 필드 누락 시 보정 재호출
  └─ 6. Generated_Reports UPSERT → 응답 반환
```

---

## 6. Gemini 입출력 구조

### 시스템 프롬프트 구성 (5파일 합산 → system_instruction)

```
system.md       ← AI 역할, HARD RULES, 톤
knowledge.md    ← AAP 기준값, 수면 교육법, 원더윅스 주령
age_policy.md   ← 월령별 수면법 허용/금지
reasoning.md    ← 추론 규칙 (확정 표현 금지, 데이터 근거 강제)
output_format.md← JSON 출력 형식 + 필드별 규칙
```

`input_template.md`는 요청마다 변수 치환 후 user prompt로 사용.

### Gemini 출력 JSON

```json
{
  "ai_comment": [
    {"type": "caution"|"good", "icon": "🌡️", "title": "...", "text": "..."}
  ],
  "sleep_guide": {
    "method_name": "퍼버법",
    "title": "...",
    "reason": "...",
    "steps": ["1단계...", "2단계...", "3단계..."],
    "kick_action": "오늘 밤 바로 실행할 것"
  },
  "age_kick": {
    "title": "8개월 분리불안",
    "text": "...",
    "is_wonder_weeks": true
  }
}
```

- `sleep_guide`: 0~2개월은 null (수면 교육 금지 월령)
- `kick_action`: Optional

---

## 7. 인증 구조

| 엔드포인트 | 인증 | 검증 내용 |
|-----------|------|---------|
| `POST /api/v1/reports/generate` | X-API-Key | `settings.ADMIN_API_KEY` 일치 |
| `GET /api/v1/reports*` | JWT Bearer | HS256 서명, `payload.ser_no` 추출 |
| `GET /api/v1/admin/*` | X-API-Key | `settings.ADMIN_API_KEY` 일치 |

JWT는 맘아이 메인 서버가 발급, 이 서버는 검증만 수행.

---

## 8. 스케줄러 (Rolling 삭제)

매주 월요일 10:00 KST 실행:
- `Weekly_Data`: 12주 이전 데이터 물리 삭제
- `Generated_Reports`: 5주 이전 데이터 물리 삭제

---

## 9. 환경변수

| 변수 | 설명 |
|------|------|
| `GEMINI_API_KEY` | Google AI Studio 발급 |
| `JWT_SECRET` | 맘아이 메인 서버와 공유하는 HS256 시크릿 |
| `ADMIN_API_KEY` | X-API-Key 헤더 인증값 (임의 문자열) |
| `DATABASE_URL` | MariaDB 연결 문자열 |
| `DB_ROOT_PASSWORD` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Docker MariaDB 설정 |
