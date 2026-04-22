# 맘아이 리포트 서버 (Mom-i Report Server)

> 영유아 수면 데이터를 분석해 AI 주간 리포트를 생성·보관·제공하는 FastAPI 백엔드 서버

---

## 시스템 흐름

```
맘아이 서버  ──POST /api/v1/reports/generate──►  AI 분석 후 리포트 JSON 반환
맘아이 앱    ──GET  /api/v1/reports           ──►  리포트 목록 (JWT 인증)
맘아이 앱    ──GET  /api/v1/reports/{id}      ──►  리포트 상세 (JWT 인증)
관리자       ──GET  /admin/stats              ──►  서버 운영 통계 (API Key)
```

- **개인정보 없음** — `ser_no`(카메라 시리얼 번호)만 식별자로 사용
- **인증 2종** — 앱 사용자: JWT(HS256) / 서버 간 호출: X-API-Key 헤더

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 프레임워크 | FastAPI + Uvicorn |
| ORM / DB | SQLAlchemy 2.0 + MariaDB 10.11 |
| AI | Google Gemini 2.5 Flash |
| 인증 | python-jose (JWT HS256 검증) |
| 스케줄러 | APScheduler (매주 월 10:00 rolling 삭제) |
| 컨테이너 | Docker + docker-compose |

---

## 프로젝트 구조

```
mom-i/
├── .env                  ← 환경변수 (커밋 금지)
├── .env.example          ← 팀원 공유용 샘플
├── docker-compose.yml
├── backend/
│   ├── run.py            ← 로컬 실행 진입점
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py      # 환경변수
│   │   │   └── security.py    # JWT 검증 / API Key 검증
│   │   ├── domain/report/
│   │   │   ├── entity.py      # WeeklyData, GeneratedReport ORM
│   │   │   └── schemas.py     # 요청/응답 Pydantic 스키마
│   │   ├── application/report/
│   │   │   └── report_service.py  # 리포트 생성 비즈니스 로직
│   │   ├── infrastructure/
│   │   │   ├── database/          # session, repository
│   │   │   ├── llm/               # Gemini 클라이언트, 시스템 프롬프트
│   │   │   └── scheduler.py       # rolling 삭제 스케줄러
│   │   └── interfaces/api/v1/
│   │       ├── report_api.py
│   │       └── admin_api.py
└── docs/
```

---

## 빠른 시작

### 도커 (권장)

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일 열어서 값 채우기

# 2. 실행
docker compose up -d

# 3. 확인
curl http://localhost:8000/health
```

### 로컬 직접 실행

```bash
# 1. 환경변수 설정 (루트에 .env 없으면)
cp .env.example .env

# 2. 가상환경 및 패키지 설치
cd backend
pip install -r requirements.txt

# 3. 실행
python run.py
```

접속: `http://localhost:8000`  
Swagger: `http://localhost:8000/docs`

---

## 환경변수 (.env)

| 변수명 | 필수 | 설명 |
|--------|------|------|
| `DB_ROOT_PASSWORD` | ✅ | MariaDB root 비밀번호 |
| `DB_NAME` | ✅ | DB 이름 (기본: `momi_db`) |
| `DB_USER` | ✅ | DB 유저명 |
| `DB_PASSWORD` | ✅ | DB 비밀번호 |
| `GEMINI_API_KEY` | ✅ | Google AI Studio에서 발급 |
| `DATABASE_URL` | ✅ | 로컬 실행 시 MariaDB 연결 문자열 |
| `JWT_SECRET` | ✅ | 맘아이 메인 서버와 공유하는 HS256 시크릿 |
| `ADMIN_API_KEY` | ✅ | 서버 간 호출 및 관리자 API용 키 |

> 도커 실행 시 `DATABASE_URL`은 docker-compose가 자동으로 컨테이너 내부 주소로 덮어씁니다.

---

## API 엔드포인트

### 리포트 (`/api/v1/reports`)

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| `POST` | `/generate` | X-API-Key | 주간 데이터 push → AI 리포트 생성 |
| `GET` | `/` | JWT | 내 리포트 목록 (최근 10건) |
| `GET` | `/{report_id}` | JWT | 리포트 상세 조회 |

### 관리자 (`/admin`)

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| `GET` | `/stats` | X-API-Key | 서버 운영 통계 |

### 시스템

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 상태 확인 |
| `GET` | `/docs` | Swagger UI |

---

## 인증 방식

**JWT (앱 사용자)**
```
Authorization: Bearer <token>
```
- 맘아이 메인 서버가 HS256으로 발급
- 이 서버는 검증만 수행 (발급 없음)
- 토큰 payload에 `ser_no` 포함 필수

**API Key (서버 간 호출 / 관리자)**
```
X-API-Key: <key>
```

---

## DB 구조

| 테이블 | 설명 |
|--------|------|
| `Weekly_Data` | 주간 원본 데이터 (AI 3주 트렌드 컨텍스트용) |
| `Generated_Reports` | AI가 생성한 리포트 (앱 재열람용) |

- 3주 초과 데이터는 매주 월요일 10:00 자동 삭제

---

## 브랜치 전략

| 브랜치 | 용도 |
|--------|------|
| `main` | 운영 배포 |
| `dev` | 통합 개발 |
| `feat/*` | 기능 개발 |
