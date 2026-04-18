# M-Take Sleep Analysis API

맘아이(mom-i) 앱에서 수면 데이터를 받아 Gemini AI로 주간 리포트를 생성하는 백엔드 서버입니다.

---

## 프로젝트 구조

```
backend/
├── app/
│   ├── main.py                        # FastAPI 앱 진입점
│   ├── core/
│   │   └── config.py                  # 환경변수 설정
│   ├── domain/
│   │   ├── sleep_data/
│   │   │   ├── entity.py              # User, DailySleepLog, EnvironmentLog, EventLog 모델
│   │   │   └── schemas.py             # 수신 데이터 Pydantic 스키마
│   │   └── report/
│   │       ├── entity.py              # GeneratedReport 모델
│   │       └── schemas.py             # 리포트 응답 스키마
│   ├── application/
│   │   ├── sleep_data/
│   │   │   └── collect_service.py     # 데이터 수신 → DB 저장
│   │   └── report/
│   │       └── report_service.py      # 7일치 집계 → AI 인사이트 → 리포트 생성
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── session.py             # DB 연결 및 세션 설정
│   │   │   └── repository/
│   │   │       ├── sleep_data_repo.py # 수면/환경/이벤트 CRUD
│   │   │       └── report_repo.py     # 리포트 이력 CRUD
│   │   ├── llm/
│   │   │   ├── gemini_client.py       # Gemini API 호출
│   │   │   └── prompts/
│   │   │       └── system_prompt.md   # AI 역할 및 규칙 프롬프트
│   │   ├── pdf/
│   │   │   └── generator.py           # reportlab PDF 생성기
│   │   └── templates/
│   │       └── report.html            # Jinja2 HTML 리포트 템플릿
│   └── interfaces/
│       └── api/v1/
│           ├── sleep_data_api.py      # POST /sleep-data/data
│           └── report_api.py          # GET /report/{user_id}
└── seed.py                            # 더미 데이터 삽입 스크립트
```

---

## 데이터 흐름

```
맘아이 앱
  │  POST /api/v1/sleep-data/data
  │  { ser_no, sleep, environment, events }
  ▼
collect_service  →  DB 저장 (Daily_Sleep_Logs / Environment_Logs / Event_Logs)
                        │
                        │  주 1회 or 요청 시
                        ▼
               report_service  →  7일치 데이터 집계
                        │
                        ▼
               gemini_client   →  AI 인사이트 코멘트 생성
                        │
                        ▼
               HTML 리포트 렌더링 (report.html)
                        │
  GET /api/v1/report/{user_id}
  ▼
맘아이 앱 (리포트 표시)
```

---

## 실행 순서

### 1단계 — 환경 설정

```bash
# backend 폴더로 이동
cd backend

# 가상환경 생성 및 활성화 (선택)
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Mac/Linux

# 패키지 설치
pip install -r requirements.txt
```

### 2단계 — 환경변수 설정

`.env.example`을 복사해서 `.env` 파일 생성 후 API 키 입력:

```bash
copy .env.example .env    # Windows
# cp .env.example .env    # Mac/Linux
```

`.env` 파일 내용:

```
PROJECT_NAME="M-Take Sleep Analysis"
GEMINI_API_KEY="여기에_발급받은_Gemini_API_키_입력"
DATABASE_URL="sqlite:///./m_take.db"
```

> Gemini API 키 발급: https://aistudio.google.com/app/apikey

### 3단계 — 더미 데이터 삽입

```bash
python seed.py
```

성공 시 출력:
```
더미 데이터 삽입 완료! user_id=1
리포트 확인: http://localhost:8000/api/v1/report/1?week_start=2025-04-07
```

### 4단계 — DB 마이그레이션 (Alembic)

스키마 변경이 있을 때 사용합니다. 처음 실행 시엔 서버가 자동으로 테이블을 생성하므로 생략 가능합니다.

```bash
# 최초 1회: 현재 모델 기준 마이그레이션 파일 생성
python -m alembic revision --autogenerate -m "init"

# DB에 적용
python -m alembic upgrade head
```

이후 모델 변경 시:

```bash
python -m alembic revision --autogenerate -m "변경내용 설명"
python -m alembic upgrade head
```

롤백이 필요하면:

```bash
python -m alembic downgrade -1
```

### 5단계 — 서버 실행

```bash
uvicorn app.main:app --reload
```

서버 시작 시 자동으로 실행되는 것들:
- DB 테이블 생성 (없을 경우)
- 주간 리포트 스케줄러 시작 (매주 월요일 09:00 KST 자동 실행)

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/sleep-data/data` | 맘아이 앱에서 일일 데이터 수신 |
| `GET`  | `/api/v1/report/preview` | Gemini 없이 샘플 리포트 미리보기 |
| `GET`  | `/api/v1/report/{user_id}` | 실제 DB 기반 주간 리포트 (HTML) |
| `GET`  | `/api/v1/report/{user_id}/pdf` | 주간 리포트 PDF 다운로드 |
| `GET`  | `/docs` | Swagger 자동 API 문서 |

### 리포트 조회 쿼리 파라미터

```
GET /api/v1/report/1?week_start=2025-04-07
```

- `week_start` 생략 시 이번 주 월요일 기준으로 자동 조회

### 맘아이 앱 → 데이터 전송 예시

```json
POST /api/v1/sleep-data/data

{
  "ser_no": "MT-00123",
  "sleep": {
    "day_gs": "9h30m",
    "day_pr": "22m",
    "measured_date": "2025-04-07"
  },
  "environment": {
    "temp_avg": 23.1,
    "temp_max": 24.2,
    "temp_min": 22.0,
    "db_max": 58,
    "measured_date": "2025-04-07"
  },
  "events": [
    { "event_type": "Crying", "event_time": "2025-04-07T02:15:00" }
  ]
}
```

---

## DB 구성

개발 환경에서는 SQLite를 사용합니다 (서버 첫 실행 시 `m_take.db` 자동 생성).

운영 환경(MySQL)으로 전환 시 `.env`의 `DATABASE_URL`만 변경:

```
DATABASE_URL="mysql+pymysql://user:password@localhost:3306/mtake"
```

MySQL 사용 시 추가 패키지 설치:

```bash
pip install pymysql cryptography
```

---

## CORS 설정

현재 `allow_origins=["*"]`로 모든 도메인을 허용합니다.  
운영 배포 시 `app/main.py`에서 맘아이 앱 실제 도메인으로 교체하세요:

```python
allow_origins=["https://app.mom-i.com"]
```

---

## 주간 리포트 자동 생성 스케줄러

서버 시작 시 APScheduler가 자동으로 실행됩니다.  
**매주 월요일 오전 9시(KST)** 에 전체 유저의 지난 주 리포트를 일괄 생성합니다.  
스케줄 변경이 필요하면 `app/infrastructure/scheduler.py`의 `CronTrigger` 값을 수정하세요.

---

## PDF 한글 출력

PDF 생성기는 Windows 기본 내장 폰트인 **맑은 고딕**을 사용합니다 (`C:/Windows/Fonts/malgun.ttf`).  
Mac/Linux 환경에서는 나눔고딕 또는 Noto Sans KR 폰트 파일을 `infrastructure/pdf/` 폴더에 넣고  
`generator.py`의 `_FONT_PATH`를 해당 경로로 변경하세요.
