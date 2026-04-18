# 맘아이 리포트 서버 (M-Take Report Server)

> 영유아 수면 데이터를 분석해 AI 주간 리포트를 생성·보관·제공하는 FastAPI 백엔드 서버

---

## 개요

맘아이 메인 서버로부터 구독 유저의 **주간 수면 데이터를 push 받아** Google Gemini AI로 분석 리포트를 생성하고, 최근 3주치를 보관해 앱에 제공합니다.

```
맘아이 서버 ──POST /api/v1/report/generate──► 리포트 JSON 즉시 리턴
맘아이 앱   ──GET  /api/v1/report/history/{ser_no}──► 최근 3주치 리포트
```

**개인정보 없음** — `ser_no`(카메라 시리얼 번호)만 식별자로 사용합니다.

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 프레임워크 | FastAPI 0.103 + Uvicorn |
| ORM / DB | SQLAlchemy 2.0 + SQLite(개발) / MySQL(운영) |
| AI | Google Gemini 1.5 Flash |
| 스케줄러 | APScheduler (매주 월 10:00 rolling 삭제) |
| 유효성 검사 | Pydantic v2 |

---

## 프로젝트 구조

```
mom-i/
├── backend/
│   ├── app/
│   │   ├── main.py                          # FastAPI 앱 진입점
│   │   ├── core/config.py                   # 환경변수 설정
│   │   ├── domain/
│   │   │   ├── report/                      # WeeklyData, GeneratedReport ORM + 스키마
│   │   │   └── etf/                         # ETFPortfolio, ETFHolding ORM + 스키마
│   │   ├── application/
│   │   │   ├── report/report_service.py     # 리포트 생성 비즈니스 로직
│   │   │   └── etf/rebalance_service.py     # ETF 리밸런싱 비즈니스 로직
│   │   ├── infrastructure/
│   │   │   ├── database/repository/         # report_repo, etf_repo
│   │   │   ├── llm/gemini_client.py         # Gemini API 클라이언트
│   │   │   ├── market/price_client.py       # 시장가 조회 클라이언트
│   │   │   └── scheduler.py                 # rolling 삭제 스케줄러
│   │   └── interfaces/api/v1/
│   │       ├── report_api.py                # 리포트 엔드포인트
│   │       └── etf_api.py                   # ETF 리밸런싱 엔드포인트
│   ├── requirements.txt
│   └── .env.example
└── docs/                                    # 설계 문서 및 작업 로그
```

---

## 빠른 시작

```bash
# 1. 의존성 설치
cd backend
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에서 GEMINI_API_KEY 입력

# 3. 서버 실행
uvicorn app.main:app --reload
```

접속: `http://localhost:8000`  
Swagger: `http://localhost:8000/docs`

---

## 환경변수

| 변수명 | 필수 | 기본값 | 설명 |
|--------|------|--------|------|
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API 키 |
| `DATABASE_URL` | | `sqlite:///./m_take.db` | DB 연결 문자열 |
| `MARKET_API_URL` | | — | ETF 시장 데이터 API URL |
| `MARKET_API_KEY` | | — | ETF 시장 데이터 API 키 (없으면 더미 가격) |

---

## API 엔드포인트

### 리포트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/report/generate` | 주간 수면 데이터 push → AI 리포트 생성 |
| `GET` | `/api/v1/report/history/{ser_no}` | 최근 3주치 리포트 조회 |

**POST /generate 요청 예시:**
```json
{
  "ser_no": "MT-00123",
  "baby_age_months": 8,
  "week_start": "2026-04-07",
  "sleep": [
    { "date": "2026-04-07", "sleep_min": 570, "restless_min": 22 },
    "... (7일치 필수)"
  ],
  "environment": { "temp_avg": 23.1, "temp_max": 24.5, "temp_min": 21.8, "db_max": 62, "db_avg": 48 },
  "events": { "cry_count": 3, "leave_count": 1 }
}
```

**응답:**
```json
{
  "ser_no": "MT-00123",
  "week_label": "2026년 4월 2주차",
  "summary": { "avg_sleep_h": 9.1, "avg_restless_min": 25, ... },
  "daily": [ { "day": "월", "sleep_h": 9.5, ... }, ... ],
  "trend": { "sleep_vs_last_week": 0.3, "restless_vs_last_week": -5, "cry_vs_last_week": -1 },
  "ai_comment": "이번 주 아기는 전반적으로 안정된 수면 패턴을 보였습니다..."
}
```

> `trend`는 이전 주 데이터가 없으면 `null` (첫 주차 사용자 정상 처리)

---

### ETF 리밸런싱

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/etf/portfolio/{ser_no}` | 포트폴리오 생성/교체 |
| `POST` | `/api/v1/etf/rebalance/{ser_no}` | 리밸런싱 주문 플랜 계산 |
| `GET` | `/api/v1/etf/rebalance/history/{ser_no}` | 이력 조회 (커서 페이지네이션) |

**커서 페이지네이션 사용법:**
```
# 첫 페이지
GET /api/v1/etf/rebalance/history/MT-00123?limit=10

# 다음 페이지 (응답의 next_cursor 사용)
GET /api/v1/etf/rebalance/history/MT-00123?cursor=42&limit=10

# has_next=false 이면 마지막 페이지
```

---

## DB 구조

```
Weekly_Data          — 주간 원본 데이터 (AI 3주 트렌드 컨텍스트용)
Generated_Reports    — 생성된 리포트 (앱 재열람용)
ETF_Portfolios       — ETF 포트폴리오
ETF_Holdings         — 포트폴리오별 ETF 보유 항목
Rebalancing_History  — 리밸런싱 실행 이력 (커서 페이지네이션 키)
```

- 모든 테이블이 `ser_no`(시리얼 번호)로 사용자 식별 — 개인정보 테이블 없음
- `Weekly_Data`, `Generated_Reports`는 3주 초과분 매주 자동 삭제

---

## 문서

| 파일 | 내용 |
|------|------|
| [`docs/dev-environment.md`](docs/dev-environment.md) | 개발 환경 설정 가이드 |
| [`docs/report_server_spec.md`](docs/report_server_spec.md) | 서버 확정 스펙 |
| [`docs/research.md`](docs/research.md) | 코드베이스 분석 보고서 |
| [`docs/plan.md`](docs/plan.md) | ETF 리밸런싱 구현 계획 |
| [`docs/work-log-2026-04-15.md`](docs/work-log-2026-04-15.md) | 작업 로그 |

---

## 브랜치 전략

| 브랜치 | 용도 |
|--------|------|
| `main` | 운영 배포 |
| `dev` | 통합 개발 |
| `feat/*` | 기능 개발 |
