# 맘아이 리포트 서버 — 전체 개발 플랜

> 최종 갱신: 2026-04-19  
> 기준 브랜치: `feat/noh`  
> 이전 plan.md(2026-04-15, ETF 구현 계획) → 현재 코드 기준 전면 재정립

---

## 1. 현재 서버 구조 한눈에 보기

```
맘아이 리포트 서버
  ├── 리포트 시스템    POST /api/v1/report/generate
  │                  GET  /api/v1/report/history/{ser_no}
  │
  └── ETF 리밸런싱   POST /api/v1/etf/portfolio/{ser_no}
                     POST /api/v1/etf/rebalance/{ser_no}
                     GET  /api/v1/etf/rebalance/history/{ser_no}
```

---

## 2. 구현 완료 현황

### 2-1. 리포트 시스템 ✅

| 파일 | 상태 | 내용 |
|------|------|------|
| `domain/report/entity.py` | ✅ | WeeklyData(breath·body_temp·monthly 컬럼 포함), GeneratedReport |
| `domain/report/schemas.py` | ✅ | BreathData, BodyTempData, MonthlySummary, BreathSummary, BodyTempSummary, TrendData(5개 지표) 등 전체 |
| `application/report/report_service.py` | ✅ | async, 캐시, DB쿼리 1회, 6단계 파이프라인 |
| `infrastructure/database/repository/report_repo.py` | ✅ | save/get/delete + get_existing_report(캐시용) |
| `infrastructure/llm/gemini_client.py` | ✅ | async, 재시도(지수백오프), 5섹션 검증, 토큰 로깅, thinking_budget=1024 |
| `infrastructure/llm/prompts/system_prompt.md` | ✅ | 월령별 권장수면·호흡수·체온 기준 명시, 5섹션 출력 형식 |
| `infrastructure/scheduler.py` | ✅ | 매주 월 10:00 KST rolling 삭제 |
| `interfaces/api/v1/report_api.py` | ✅ | async 엔드포인트 2개 |

**리포트 생성 파이프라인 (6 Steps):**
```
Step 1  원본 저장      Weekly_Data upsert (breath·body_temp·monthly 포함)
Step 2  캐시 확인      기존 리포트 있으면 Gemini 재호출 없이 즉시 반환
Step 3  이전 조회      get_recent_weekly_data(weeks=2) — DB 1회
Step 4  집계           summary / daily / breath_summary / body_temp_summary / trend
Step 5  AI 생성        await generate_insight() — 재시도·검증·로깅 포함
Step 6  저장·반환      Generated_Reports upsert → GenerateReportResponse
```

**EMTAKE 프로토콜 반영 완료:**
```
CMD: SleepData  → sleep (7일치) + monthly (month_gs/month_pr)
CMD: IndoorTemp → environment.temp_*
CMD: dB         → environment.db_*
CMD: Breath     → breath (breath_min/max/avg)   ← 신규 추가
CMD: Temp       → body_temp (체온 상승)          ← 신규 추가
```

---

### 2-2. ETF 리밸런싱 시스템 ✅

| 파일 | 상태 | 내용 |
|------|------|------|
| `domain/etf/entity.py` | ✅ | ETFPortfolio, ETFHolding, RebalancingHistory |
| `domain/etf/schemas.py` | ✅ | CreatePortfolioRequest, RebalanceResponse, HistoryPageResponse 등 |
| `infrastructure/database/repository/etf_repo.py` | ✅ | upsert_portfolio, cursor 페이지네이션 |
| `infrastructure/market/price_client.py` | ✅ | 더미 가격 fallback, 실 API 연동 준비 완료 |
| `application/etf/rebalance_service.py` | ✅ | drift 5% 임계값 BUY/SELL/HOLD 알고리즘 |
| `interfaces/api/v1/etf_api.py` | ✅ | 포트폴리오 CRUD, 리밸런싱, 커서 페이지네이션 |

---

### 2-3. 공통 인프라 ✅

| 항목 | 상태 | 내용 |
|------|------|------|
| `main.py` | ✅ | 두 라우터 등록, startup 훅 |
| `core/config.py` | ✅ | GEMINI_API_KEY, DATABASE_URL, MARKET_API_* |
| `backend/.env` | ✅ | GEMINI_API_KEY 입력 완료 |
| `requirements.txt` | ✅ | 최신화 완료 |
| `application/sleep_data/simulator_service.py` | ✅ | EMTAKE 전체 필드 더미 생성 |
| `gemini-2.5-flash` | ✅ | 모델 교체 완료 |

---

## 3. 미완료 — 남은 작업

### 🔴 즉시 필요 (서버 실행 전)

#### [P0-1] DB 재생성
새 컬럼(`breath_json`, `body_temp_json`, `monthly_json`)이 추가됐지만
`create_tables()`는 기존 테이블을 ALTER 하지 않음.

```bash
# 개발 환경: SQLite 파일 삭제 후 재시작
cd backend
rm momi.db
uvicorn app.main:app --reload
```

#### [P0-2] 서버 실행 검증
```bash
cd backend
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs 에서 Swagger UI 확인
```

#### [P0-3] 리포트 생성 E2E 테스트
시뮬레이터로 실제 POST 호출 검증:
```python
from app.application.sleep_data.simulator_service import make_multi_week_dummy
import httpx

weeks = make_multi_week_dummy(num_weeks=3)
for w in weeks:
    r = httpx.post("http://localhost:8000/api/v1/report/generate", json=w)
    print(r.status_code, r.json().get("week_label"))

# 3번째 응답에 trend 블록 포함 여부 확인
# 동일 주차 재전송 시 캐시 히트 로그 확인
```

---

### 🟡 단기 (이번 스프린트)

#### [P1-1] ETF API async 전환
리포트 API는 async 전환 완료. ETF API는 아직 sync.
일관성 + 향후 async DB 전환 대비.

```python
# etf_api.py
# def create_portfolio → async def create_portfolio
# def run_rebalance    → async def run_rebalance
# def get_history      → async def get_history
```

#### [P1-2] 로깅 설정 체계화
현재 각 파일에서 `logging.getLogger(__name__)` 사용 중이지만
`main.py`에 전역 로그 포맷 설정이 없음.

```python
# main.py에 추가
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
```

#### [P1-3] 헬스체크 엔드포인트
배포 환경에서 서버 상태 모니터링용.

```python
# main.py 또는 별도 health_api.py
@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}
```

#### [P1-4] `.env.example` 최신화
현재 `.env.example`이 구버전이었으나 최신화 완료.
신규 팀원 온보딩용으로 현행화 필요.

---

### 🟢 중기 (다음 스프린트)

#### [P2-1] pytest 테스트 코드 작성
현재 테스트 파일 없음. 최소한 아래 3개 커버 필요:

```
tests/
├── test_report_service.py
│     ├── test_generate_report_first_week()   → trend=None 확인
│     ├── test_generate_report_cache_hit()    → Gemini 재호출 없는지 확인
│     └── test_generate_report_3weeks()       → trend 블록 정상 포함 확인
├── test_breath_analysis.py
│     ├── test_normal_breath_range()
│     └── test_abnormal_breath_range()
└── test_etf_rebalance.py
      ├── test_drift_below_threshold()        → HOLD 처리 확인
      └── test_cursor_pagination()
```

#### [P2-2] Alembic 마이그레이션 적용
현재 `create_tables()` 런타임 생성 방식.
운영 전 Alembic으로 전환해 스키마 버전 관리 필요.

```bash
cd backend
alembic init alembic
alembic revision --autogenerate -m "add breath body_temp monthly columns"
alembic upgrade head
```

#### [P2-3] 토큰 사용량 DB 저장
현재 로그로만 기록. 구독자별 비용 추적 및 이상 감지를 위해 DB 저장 권장.

```python
# 신규 테이블 또는 Generated_Reports에 컬럼 추가
token_input:  int   # 입력 토큰
token_output: int   # 출력 토큰
```

---

### 🔵 장기 / 운영 전환

#### [P3-1] 인증/인가
현재 모든 엔드포인트 인증 없음.
`POST /generate`는 맘아이 서버만 호출 가능해야 함.

```python
# 방식 1: API 키 헤더 검증
# X-API-Key: {shared_secret}

# 방식 2: JWT (맘아이 서버에서 발급)
```

#### [P3-2] CORS 도메인 제한
```python
# 현재 (위험)
allow_origins=["*"]

# 운영
allow_origins=["https://app.momi.kr", "https://api.momi.kr"]
```

#### [P3-3] async SQLAlchemy 전환
MySQL 운영 시 sync SQLAlchemy가 이벤트 루프 blocking 발생.
`sqlalchemy.ext.asyncio` + `AsyncSession`으로 마이그레이션 필요.

#### [P3-4] PDF 출력 연결
`infrastructure/pdf/generator.py` 스켈레톤 존재.
현재 어떤 라우터에도 연결 안 됨.
앱 팀이 JSON 렌더링 vs PDF 다운로드 방향 결정 후 연결.

#### [P3-5] 시장 데이터 API 실제 연동
`price_client.py`가 `MARKET_API_KEY` 없으면 더미 가격 반환 중.
실제 금융 데이터 API(한국투자증권 API, Alpha Vantage 등) 연동 필요.

---

## 4. 전체 우선순위 요약

```
🔴 P0 — 지금 당장 (서버 실행 전)
  P0-1  DB 재생성 (momi.db 삭제 후 재시작)
  P0-2  uvicorn 실행 + /docs Swagger 확인
  P0-3  시뮬레이터로 리포트 생성 E2E 테스트

🟡 P1 — 이번 스프린트
  P1-1  ETF API async 전환
  P1-2  main.py 로깅 포맷 설정
  P1-3  /health 엔드포인트 추가
  P1-4  .env.example 최신화

🟢 P2 — 다음 스프린트
  P2-1  pytest 테스트 작성 (report + breath + etf)
  P2-2  Alembic 마이그레이션 전환
  P2-3  토큰 사용량 DB 저장

🔵 P3 — 운영 전환
  P3-1  인증/인가 (API 키 or JWT)
  P3-2  CORS 도메인 제한
  P3-3  async SQLAlchemy 전환
  P3-4  PDF 라우터 연결
  P3-5  시장 데이터 실 API 연동
```

---

## 5. 역할별 담당 매핑

| 역할 | 담당 작업 |
|------|----------|
| **AI 리포트 (D)** | P0-3, P1-3, P2-1(report·breath 테스트), P2-3, Gemini 프롬프트 고도화 |
| **도메인 지식** | system_prompt.md 섹션 기준값 검수, 월령별 권장 기준 업데이트 |
| **백엔드 공통** | P0-1, P0-2, P1-1, P1-2, P1-4, P2-2, P3-1, P3-2, P3-3 |
| **ETF** | P2-1(etf 테스트), P3-5 |
| **인프라/배포** | P3-1, P3-2, P3-3 |

---

## 6. API 전체 목록 (현재 구현 기준)

| 메서드 | 경로 | 호출자 | 상태 |
|--------|------|--------|------|
| `POST` | `/api/v1/report/generate` | 맘아이 서버 | ✅ async + 캐시 + 재시도 |
| `GET` | `/api/v1/report/history/{ser_no}` | 맘아이 앱 | ✅ async |
| `POST` | `/api/v1/etf/portfolio/{ser_no}` | 맘아이 서버 | ✅ (sync) |
| `POST` | `/api/v1/etf/rebalance/{ser_no}` | 맘아이 서버 | ✅ (sync) |
| `GET` | `/api/v1/etf/rebalance/history/{ser_no}` | 맘아이 앱 | ✅ (sync) |
| `GET` | `/` | 모니터링 | ✅ |
| `GET` | `/health` | 모니터링 | ❌ 미구현 |

---

## 7. 데이터베이스 테이블 전체 목록

| 테이블 | 역할 | 보존 기간 |
|--------|------|----------|
| `Weekly_Data` | 주간 원본(수면·환경·호흡·체온·월간) | 3주 rolling 삭제 |
| `Generated_Reports` | AI 생성 리포트 전체 | 3주 rolling 삭제 |
| `ETF_Portfolios` | 사용자 포트폴리오 | 무기한 |
| `ETF_Holdings` | 포트폴리오 내 ETF 보유 | 무기한 (포트폴리오 교체 시 재삽입) |
| `Rebalancing_History` | 리밸런싱 이력 (커서 페이지네이션) | 무기한 |

---

## 8. 개발 환경 빠른 시작

```bash
# 1. 의존성 설치
cd backend
pip install -r requirements.txt

# 2. .env 확인 (GEMINI_API_KEY 입력 여부)
cat .env

# 3. DB 초기화 (기존 DB가 있으면 삭제 필수)
rm -f momi.db

# 4. 서버 실행
uvicorn app.main:app --reload --port 8000

# 5. Swagger UI 확인
# http://localhost:8000/docs

# 6. 리포트 생성 테스트 (Python 콘솔)
# from app.application.sleep_data.simulator_service import make_dummy_week
# import httpx
# r = httpx.post("http://localhost:8000/api/v1/report/generate", json=make_dummy_week())
# print(r.json())
```
