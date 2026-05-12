# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 실행 명령어

### 백엔드

```bash
# 패키지 설치 (backend/ 디렉토리에서)
pip install -r backend/requirements.txt

# 로컬 서버 실행
cd backend && python run.py          # http://localhost:8000
# Swagger UI: http://localhost:8000/docs

# DB 마이그레이션
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "설명"
```

### 프론트엔드

```bash
# frontend/ 디렉토리에서
npm install
npm run dev      # http://localhost:5173
npm run build    # dist/ 출력
```

### 도커 (MariaDB 포함 전체 실행)

```bash
docker compose up -d        # 백그라운드 실행
docker compose down         # 종료
docker compose logs -f app  # 로그 확인
```

### 테스트

```bash
cd backend && pytest
cd backend && pytest tests/path/to/test.py::test_name  # 단일 테스트
cd backend && pytest --cov=app                          # 커버리지
```

---

## 환경변수

환경변수는 **프로젝트 루트 `.env` 단일 파일**로 관리한다 (`backend/.env` 없음).

`config.py`에서 `Path(__file__).resolve().parents[3] / ".env"` 로 절대경로 로드.  
`docker-compose.yml`의 `app` 서비스는 `env_file: .env` + `DATABASE_URL` 오버라이드(컨테이너 내부 DB 호스트명 `db`)로 동작.

```bash
cp .env.example .env  # 팀원 온보딩 시
```

---

## 아키텍처

### 시스템 위치

이 서버는 **MSA 구조의 리포트 전담 마이크로서비스**다.  
맘아이 메인 서버가 주간 데이터를 push하면 Gemini로 분석해 리포트 JSON을 반환하고, 앱이 재열람할 수 있도록 DB에 보관한다.

```
EMTAKE 카메라 → 맘아이 서버 ──POST /generate──► 이 서버 ──► Gemini API
맘아이 앱 ──────────────────────GET /reports───► 이 서버 ──► DB
```

**JWT를 발급하지 않는다** — 맘아이 메인 서버가 발급한 HS256 토큰을 검증만 한다.

### 백엔드 레이어 구조

```
interfaces/api/v1/   → FastAPI 라우터 (HTTP 경계)
application/report/  → report_service.py (비즈니스 로직 전체)
domain/report/       → entity.py (ORM), schemas.py (Pydantic)
infrastructure/
  database/          → session.py, repository/report_repo.py
  llm/               → gemini_client.py, prompts/system_prompt.md
  scheduler.py       → APScheduler (rolling 삭제)
core/
  config.py          → pydantic-settings, 루트 .env 로드
  security.py        → JWT 검증 / API Key 검증
```

### 리포트 생성 흐름 (`report_service.generate_report`)

1. `Weekly_Data` upsert (항상 — 캐시 히트여도)
2. `Generated_Reports` 캐시 확인 → 있으면 Gemini 재호출 없이 즉시 반환
3. 이전 2주치 `Weekly_Data` 1회 조회 (trend + AI 컨텍스트 공용)
4. 집계: summary / daily / breath / body_temp / trend
5. `gemini_client.generate_insight()` — async, 최대 3회 재시도, JSON 필드 검증 후 재호출
6. `Generated_Reports` upsert → 응답 반환

### Gemini 출력 구조

`system_prompt.md`가 정의하는 JSON 구조:
```json
{
  "ai_comment": [{"type": "caution"|"good", "icon": "…", "title": "…", "text": "…"}],
  "sleep_guide": {"method_name": "…", "title": "…", "reason": "…", "steps": ["…"]},
  "age_kick":    {"title": "…", "text": "…", "is_wonder_weeks": true}
}
```
`gemini_client._validate_json()`이 필드 존재·타입을 검증하고, 누락 시 보정 프롬프트로 재호출.

### DB 테이블

| 테이블 | 역할 | 보존 기간 |
|--------|------|---------|
| `Weekly_Data` | 주간 원본 (Gemini AI 고도화 컨텍스트용) | 12주 rolling |
| `Generated_Reports` | 생성된 리포트 전체 JSON (앱 열람용) | 5주 rolling |

스케줄러가 매주 월요일 10:00 KST에 물리 삭제. 두 테이블의 보존 기간이 다름.  
`create_tables()`는 DDL 자동 생성용 (startup 시 실행). 스키마 변경은 Alembic 사용.

### 인증

- **X-API-Key** (`security.verify_api_key`): `POST /generate`, `GET /admin/stats`
- **JWT Bearer** (`security.get_current_ser_no`): `GET /reports`, `GET /reports/{id}`  
  → payload의 `ser_no`를 추출해 DB 격리에 사용

### 프론트엔드

`frontend/` — Vite + TypeScript (jang 담당).  
`frontend/src/main.ts`가 `mockData.ts`를 읽어 정적 리포트를 렌더링.  
`frontend/demo.html` — 백엔드 API를 실제 호출하는 테스트 페이지 (noh 담당). `http://localhost:5173/demo.html`로 접속.

---

## 코드 작성 규칙

- 독립적으로 추가하는 메서드/함수는 파일 **맨 아래**에 작성 (git 충돌 방지). 순서가 의미를 가지는 경우(if-else 분기 등)는 예외.
- Pydantic v2: `model_validate()` 사용, `dict()` 대신 `model_dump(mode="json")`.
- DB에서 꺼낸 JSON을 Pydantic 모델로 변환할 때 `Model(**json_dict)` 대신 `Model.model_validate(json_dict)`.

## 행동 지침

Behavioral guidelines to reduce common LLM coding mistakes.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
