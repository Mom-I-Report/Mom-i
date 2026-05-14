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
| AI | google-genai (`gemini-3.1-flash-lite`) |
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

> 상세 플로우: [docs/noh/시스템-흐름-2026-05-12.md](./noh/시스템-흐름-2026-05-12.md)

요약: Weekly_Data UPSERT → 캐시 확인 → 이전 2주치 조회 → 집계(summary/daily/breath/body_temp/trend) → Gemini 비동기 호출(최대 5회 재시도, 4필드 검증) → Generated_Reports UPSERT → 응답 반환

---

## 6. Gemini 입출력 구조

> 상세 내용: [docs/noh/llm.md](./noh/llm.md)

요약: 5개 프롬프트 파일(`system·knowledge·age_policy·reasoning·output_format`)을 조합한 system_instruction + `input_template.md` 기반 user prompt → Gemini `gemini-3.1-flash-lite` 호출 → `ai_comment / sleep_guide / age_kick / parent_message` 4필드 JSON 반환

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
