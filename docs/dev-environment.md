# 개발 환경 가이드

| 항목 | 내용 |
|------|------|
| **작성일** | 2026-04-15 |
| **작성자** | nohojong |

---

## 1. 개발 환경 스펙

| 항목 | 값 |
|------|-----|
| OS | Windows 11 Home (Build 26200) |
| Python | 3.12.9 |
| 패키지 관리자 | Miniforge (conda) + pip |
| Python 실행 경로 | `C:\Users\xntn4\miniforge3\python.exe` |
| 개발 DB | SQLite (`backend/m_take.db`, 자동 생성) |
| 운영 DB | MySQL (`.env`의 `DATABASE_URL`로 전환) |

---

## 2. 빠른 시작

```bash
# 1. 저장소 클론
git clone <repo-url>
cd mom-i/backend

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일에서 GEMINI_API_KEY 입력 (필수)

# 4. 서버 기동
uvicorn app.main:app --reload
```

접속: `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`

---

## 3. 환경변수 (.env)

| 변수명 | 필수 | 기본값 | 설명 |
|--------|------|--------|------|
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API 키 |
| `DATABASE_URL` | | `sqlite:///./m_take.db` | DB 연결 문자열 |
| `MARKET_API_URL` | | `""` | ETF 시장 데이터 API URL |
| `MARKET_API_KEY` | | `""` | ETF 시장 데이터 API 키 (없으면 더미 가격 사용) |

**.env.example 템플릿:**
```
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///./m_take.db
MARKET_API_URL=
MARKET_API_KEY=
```

---

## 4. 패키지 의존성

### 4.1 핵심 패키지 (실제 설치 기준)

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `fastapi` | 0.135.3 | 웹 프레임워크 |
| `uvicorn` | 0.44.0 | ASGI 서버 |
| `pydantic` | 2.13.0 | 요청/응답 유효성 검사 |
| `pydantic-settings` | 2.13.1 | 환경변수 설정 관리 |
| `google-generativeai` | 0.8.6 | Gemini AI 클라이언트 |
| `APScheduler` | 3.11.2 | 주간 rolling 삭제 스케줄러 |
| `SQLAlchemy` | 2.0.49 | ORM |
| `alembic` | 1.18.4 | DB 마이그레이션 |
| `httpx` | 0.28.1 | ETF 시장가 API 호출 |

### 4.2 선택 패키지

| 패키지 | 용도 | 설치 방법 |
|--------|------|-----------|
| `reportlab` | PDF 리포트 생성 스켈레톤 | `pip install reportlab==4.2.2` |
| `pymysql` | 운영 MySQL 연결 | `pip install pymysql cryptography` |

### 4.3 테스트 패키지

```bash
pip install pytest==7.4.2 pytest-asyncio==0.21.1 pytest-cov==4.1.0
```

### 4.4 제거된 패키지 (구 기능 잔재)

아래 패키지는 `requirements.txt`에서 제거됨. 일별 수면 수집 → 주간 push 방식 전환으로 불필요해짐.

| 패키지 | 제거 이유 |
|--------|-----------|
| `jinja2` | HTML 리포트 렌더링 기능 제거 |
| `aiofiles` | 비동기 파일 I/O 불필요 (JSON 리턴 방식) |
| `python-dateutil` | `sleep_min: int` 도입으로 날짜 파싱 불필요 |

---

## 5. 프로젝트 구조

```
mom-i/
├── backend/
│   ├── app/
│   │   ├── main.py                              # FastAPI 앱 진입점
│   │   ├── core/
│   │   │   └── config.py                        # 환경변수 (pydantic-settings)
│   │   ├── domain/
│   │   │   ├── report/
│   │   │   │   ├── entity.py                    # WeeklyData, GeneratedReport ORM
│   │   │   │   └── schemas.py                   # 요청/응답 Pydantic 스키마
│   │   │   └── etf/
│   │   │       ├── entity.py                    # ETFPortfolio, ETFHolding, RebalancingHistory
│   │   │       └── schemas.py                   # ETF 요청/응답 스키마
│   │   ├── application/
│   │   │   ├── report/
│   │   │   │   └── report_service.py            # 리포트 생성 비즈니스 로직
│   │   │   ├── etf/
│   │   │   │   └── rebalance_service.py         # ETF 리밸런싱 알고리즘
│   │   │   └── sleep_data/
│   │   │       └── simulator_service.py         # 테스트용 더미 데이터 생성기 (스켈레톤)
│   │   ├── infrastructure/
│   │   │   ├── database/
│   │   │   │   ├── session.py                   # DB 세션 / 테이블 생성
│   │   │   │   └── repository/
│   │   │   │       ├── report_repo.py           # WeeklyData, GeneratedReport CRUD
│   │   │   │       └── etf_repo.py              # ETF CRUD + 커서 페이지네이션
│   │   │   ├── llm/
│   │   │   │   └── gemini_client.py             # Gemini 1.5 Flash 클라이언트
│   │   │   ├── market/
│   │   │   │   └── price_client.py              # ETF 시장가 API (더미 fallback)
│   │   │   ├── pdf/
│   │   │   │   └── generator.py                 # PDF 생성기 스켈레톤 (reportlab)
│   │   │   └── scheduler.py                     # 3주 rolling 삭제 (매주 월 10:00)
│   │   └── interfaces/
│   │       └── api/v1/
│   │           ├── report_api.py                # POST /generate, GET /history/{ser_no}
│   │           └── etf_api.py                   # ETF 3개 엔드포인트
│   ├── requirements.txt
│   └── .env.example
├── docs/                                        # 설계 문서
└── README.md
```

---

## 6. DB 관리

### 6.1 SQLite (개발)

서버 첫 기동 시 `backend/m_take.db` 자동 생성 — 별도 설정 불필요.

생성 테이블:
```
Weekly_Data          UNIQUE(ser_no, week_start)
Generated_Reports    UNIQUE(ser_no, week_start)
ETF_Portfolios
ETF_Holdings
Rebalancing_History
```

### 6.2 MySQL (운영)

```bash
# .env 수정
DATABASE_URL=mysql+pymysql://user:password@host:3306/dbname

# 추가 패키지 설치
pip install pymysql cryptography

# Alembic 마이그레이션 생성
python -m alembic revision --autogenerate -m "init report server"
python -m alembic upgrade head
```

---

## 7. API 테스트

### 7.1 Swagger UI

`http://localhost:8000/docs` — 브라우저에서 직접 호출 가능

### 7.2 curl 예시

```bash
# 리포트 생성
curl -X POST http://localhost:8000/api/v1/report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "ser_no": "MT-00123",
    "baby_age_months": 8,
    "week_start": "2026-04-07",
    "sleep": [
      {"date": "2026-04-07", "sleep_min": 570, "restless_min": 22},
      {"date": "2026-04-08", "sleep_min": 540, "restless_min": 30},
      {"date": "2026-04-09", "sleep_min": 600, "restless_min": 15},
      {"date": "2026-04-10", "sleep_min": 510, "restless_min": 35},
      {"date": "2026-04-11", "sleep_min": 580, "restless_min": 20},
      {"date": "2026-04-12", "sleep_min": 560, "restless_min": 25},
      {"date": "2026-04-13", "sleep_min": 590, "restless_min": 18}
    ],
    "environment": {"temp_avg": 23.1, "temp_max": 24.5, "temp_min": 21.8, "db_max": 62, "db_avg": 48},
    "events": {"cry_count": 3, "leave_count": 1}
  }'

# 이력 조회
curl http://localhost:8000/api/v1/report/history/MT-00123

# ETF 포트폴리오 생성
curl -X POST http://localhost:8000/api/v1/etf/portfolio/MT-00123 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "글로벌 분산 포트폴리오",
    "total_asset": 10000000,
    "holdings": [
      {"ticker": "SPY",  "name": "S&P500 ETF",  "target_weight": 0.4, "quantity": 10},
      {"ticker": "QQQ",  "name": "나스닥100 ETF", "target_weight": 0.3, "quantity": 8},
      {"ticker": "TLT",  "name": "미국장기채 ETF", "target_weight": 0.2, "quantity": 20},
      {"ticker": "GLD",  "name": "금 ETF",        "target_weight": 0.1, "quantity": 5}
    ]
  }'
```

### 7.3 더미 데이터 시뮬레이터

```python
# Python 셸에서 실행
from app.application.sleep_data.simulator_service import make_multi_week_dummy
import httpx, json

# 3주치 더미 데이터 생성 후 서버에 순차 push
weeks = make_multi_week_dummy("MT-TEST", baby_age_months=10, num_weeks=3)
for w in weeks:
    r = httpx.post("http://localhost:8000/api/v1/report/generate", json=w)
    print(r.status_code, r.json().get("week_label"))
```

---

## 8. 알려진 이슈 / 주의사항

| 항목 | 내용 |
|------|------|
| `google-generativeai` FutureWarning | `google.genai` 패키지로 전환 권장 (현재 동작은 정상) |
| `GEMINI_API_KEY` 미설정 | 서버는 기동되지만 `/generate` 호출 시 AI 단계에서 오류 발생 |
| `MARKET_API_KEY` 미설정 | 더미 가격으로 자동 fallback — ETF 리밸런싱 테스트 가능 |
| CORS | 현재 `allow_origins=["*"]` — 운영 배포 전 도메인 제한 필요 |
| SQLite 동시성 | 개발 전용. 운영은 반드시 MySQL 사용 |
