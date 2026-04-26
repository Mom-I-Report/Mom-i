# 맘아이 리포트 서버 (Mom-i Report Server)

> 영유아 수면 데이터를 분석해 AI 주간 리포트를 생성·보관·제공하는 FastAPI 마이크로서비스

---

## 시스템 위치

이 서버는 MSA 구조의 **리포트 전담 마이크로서비스**다.  
맘아이 메인 서버가 주간 데이터를 push하면 Gemini로 분석해 리포트 JSON을 반환하고, 앱이 재열람할 수 있도록 DB에 보관한다.

```
EMTAKE 카메라 → 맘아이 서버 ──POST /generate──► 이 서버 ──► Gemini API
맘아이 앱 ─────────────────────GET /reports───► 이 서버 ──► DB
관리자 ────────────────────────GET /admin/stats► 이 서버 ──► DB
```

- **개인정보 없음** — `ser_no`(카메라 시리얼 번호)만 식별자로 사용. 이름·생년월일 일절 저장 안 함
- **JWT 발급 없음** — 맘아이 메인 서버가 발급한 HS256 토큰을 검증만 함

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 프레임워크 | FastAPI + Uvicorn |
| ORM / DB | SQLAlchemy 2.0 + MariaDB 10.11 |
| AI | Google Gemini 3 Flash Preview (`gemini-3-flash-preview`) |
| 인증 | python-jose (JWT HS256 검증) |
| 스케줄러 | APScheduler (매주 월요일 10:00 KST rolling 삭제) |
| 컨테이너 | Docker + docker-compose |

---

## 프로젝트 구조

```
mom-i/
├── .env                        ← 환경변수 (커밋 금지)
├── .env.example                ← 팀원 온보딩용 샘플
├── docker-compose.yml
├── backend/
│   ├── run.py                  ← 로컬 실행 진입점
│   ├── requirements.txt
│   ├── alembic/                ← DB 마이그레이션
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py           # 환경변수 (루트 .env 로드)
│       │   └── security.py         # JWT 검증 / API Key 검증
│       ├── domain/report/
│       │   ├── entity.py           # WeeklyData, GeneratedReport ORM
│       │   └── schemas.py          # 요청/응답 Pydantic 스키마
│       ├── application/report/
│       │   └── report_service.py   # 리포트 생성 비즈니스 로직 (6단계)
│       ├── infrastructure/
│       │   ├── database/           # session.py, report_repo.py
│       │   ├── llm/
│       │   │   ├── gemini_client.py    # Gemini 비동기 클라이언트
│       │   │   └── prompts/            # 프롬프트 6개 파일 (아래 참고)
│       │   └── scheduler.py        # rolling 삭제 스케줄러
│       └── interfaces/api/v1/
│           ├── report_api.py
│           └── admin_api.py
├── frontend/
│   ├── src/                    ← Vite + TypeScript (jang 담당)
│   └── demo.html               ← 백엔드 API 직접 호출 테스트 페이지 (noh 담당)
└── docs/
    ├── noh/                    ← AI 리포트 서버 관련 문서
    └── jang/                   ← 프론트엔드 관련 문서
```

---

## 빠른 시작

### 도커 (권장)

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일 열어서 값 채우기 (아래 환경변수 표 참고)

# 2. 실행
docker compose up -d

# 3. DB 마이그레이션 (최초 1회)
docker compose exec app alembic revision --autogenerate -m "initial"
docker compose exec app alembic upgrade head

# 4. 서버 확인
curl http://localhost:8000/health
# → {"status": "ok", "version": "0.2.0"}
```

### 로컬 직접 실행

```bash
# 1. 환경변수 설정
cp .env.example .env

# 2. 패키지 설치
cd backend
pip install -r requirements.txt

# 3. DB 마이그레이션 (MariaDB가 실행 중이어야 함)
alembic revision --autogenerate -m "initial"
alembic upgrade head

# 4. 서버 실행
python run.py
```

접속: `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`

---

## 환경변수 (.env)

| 변수명 | 필수 | 설명 |
|--------|------|------|
| `GEMINI_API_KEY` | ✅ | Google AI Studio에서 발급 |
| `JWT_SECRET` | ✅ | 맘아이 메인 서버와 **공유하는** HS256 시크릿 |
| `ADMIN_API_KEY` | ✅ | 릴레이 서버가 X-API-Key 헤더에 넣을 임의 문자열 |
| `DB_ROOT_PASSWORD` | ✅ | MariaDB root 비밀번호 |
| `DB_NAME` | ✅ | DB 이름 (기본: `momi_db`) |
| `DB_USER` | ✅ | DB 유저명 |
| `DB_PASSWORD` | ✅ | DB 비밀번호 |
| `DATABASE_URL` | ✅ | 로컬 실행 시 MariaDB 연결 문자열 |

> `JWT_SECRET`은 맘아이 메인 서버 것과 **완전히 동일**해야 한다. 다르면 앱 로그인 후 리포트 조회 시 401 반환.  
> 도커 실행 시 `DATABASE_URL`은 docker-compose가 컨테이너 내부 주소로 자동 덮어씀.

---

## API 엔드포인트

### 리포트 (`/api/v1/reports`)

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| `POST` | `/generate` | X-API-Key | 주간 데이터 push → AI 리포트 생성 |
| `GET` | `` | JWT | 내 리포트 목록 (최근 10건) |
| `GET` | `/{report_id}` | JWT | 리포트 상세 조회 |

### 관리자 (`/admin`)

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| `GET` | `/stats` | X-API-Key | 전체 리포트 수, 활성 기기 수, 오늘/이번 주 생성 수 등 |

### 시스템

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 상태 (`{"status": "ok"}`) |
| `GET` | `/docs` | Swagger UI |

---

## 인증 방식

**JWT (앱 사용자)**
```
Authorization: Bearer <token>
```
- 맘아이 메인 서버가 HS256으로 발급
- 이 서버는 검증만 수행 (발급 없음)
- 토큰 payload에 `ser_no` 클레임 포함 필수

**API Key (서버 간 호출 / 관리자)**
```
X-API-Key: <ADMIN_API_KEY 값>
```

---

## 리포트 생성 흐름

`POST /generate` 호출 시 `report_service.generate_report()`가 아래 6단계를 실행한다.

```
1. Weekly_Data upsert          — 원본 데이터 항상 저장 (캐시 히트여도)
2. 캐시 확인                   — 동일 주차 리포트 있으면 Gemini 재호출 없이 즉시 반환
3. 이전 2주치 조회 (1회)       — 트렌드 계산 + AI 컨텍스트 공용
4. 집계                        — 주간 요약 / 일별 / 호흡 / 체온 / 트렌드
5. Gemini 비동기 호출          — 최대 3회 재시도, 3필드 검증, JSON 보정 재호출
6. Generated_Reports upsert    — 리포트 저장 후 응답 반환
```

---

## AI 리포트 출력 구조

Gemini가 반환하는 JSON 구조 (`GenerateReportResponse`의 AI 생성 필드):

```json
{
  "ai_comment": [
    {
      "type": "caution",
      "icon": "🌡️",
      "title": "체온 주의",
      "text": "이번 주 평균 체온이 37.3°C로..."
    }
  ],
  "sleep_guide": {
    "method_name": "퍼버법",
    "title": "시도해볼 수 있는 수면 가이드: 퍼버법",
    "reason": "이번 주 뒤척임이 평균 35분으로...",
    "steps": ["1단계: ...", "2단계: ...", "3단계: ..."],
    "kick_action": "오늘 밤 재우기 30분 전 모든 자극을 차단하세요"
  },
  "age_kick": {
    "title": "8개월 분리불안",
    "text": "이 시기 아기는...",
    "is_wonder_weeks": true
  }
}
```

- `sleep_guide`: 0~2개월 아기는 `null` (수면 교육 전체 금지)
- `is_wonder_weeks`: `baby_age_months × 4.3 ≈ 주령` 기준, ±1주 이내면 `true`

---

## 프롬프트 구조

`backend/app/infrastructure/llm/prompts/` 아래 6개 파일로 역할을 분리해 관리한다.

| 파일 | 역할 |
|------|------|
| `system.md` | AI 역할 정의, HARD RULES 7개, 응답 톤/스타일 |
| `knowledge.md` | 도메인 지식 (AAP 기준, 수면 교육법 7개, 원더윅스 주령) |
| `age_policy.md` | 월령별 수면법 허용/금지 정책 (0개월~13개월+) |
| `reasoning.md` | 추론 규칙 (확정 표현 금지, 데이터 기반 설명 강제) |
| `output_format.md` | JSON 출력 형식 + 필드별 작성 규칙 |
| `input_template.md` | user prompt 템플릿 (변수 치환 방식) |

서버 시작 시 `system.md → knowledge.md → age_policy.md → reasoning.md → output_format.md` 순으로 합쳐 `system_instruction`으로 주입. `input_template.md`는 요청마다 변수 치환 후 user prompt로 사용.

---

## DB 구조

| 테이블 | 역할 | 보존 기간 |
|--------|------|---------|
| `Weekly_Data` | 주간 원본 데이터 (AI 트렌드 컨텍스트용) | **12주** rolling |
| `Generated_Reports` | 생성된 리포트 전체 JSON (앱 열람용) | **5주** rolling |

스케줄러가 매주 월요일 10:00 KST에 자동 물리 삭제. 소프트 삭제 없음.

---

## 브랜치 전략

| 브랜치 | 용도 |
|--------|------|
| `main` | 운영 배포 |
| `dev` | 통합 개발 |
| `feat/noh` | AI 리포트 서버 (noh 담당) |
| `feat/jang` | 프론트엔드 (jang 담당) |
