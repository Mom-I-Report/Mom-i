# 개발 환경 가이드

> 최종 갱신: 2026-05-14

---

## 1. 개발 환경 스펙

| 항목 | 값 |
|------|-----|
| OS | Windows 11 Home (Build 26200) |
| Python | 3.12.9 |
| 패키지 관리자 | Miniforge (conda) + pip |
| Python 실행 경로 | `C:\Users\xntn4\miniforge3\python.exe` |
| Node.js | 최신 LTS (npm 포함) |
| DB (개발) | MariaDB 10.11 — Docker Compose로 기동 |

---

## 2. 빠른 시작

### 도커 (권장)

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일에서 값 채우기 (아래 환경변수 표 참고)

# 2. 실행
docker compose up -d

# 3. DB 마이그레이션 (최초 1회)
docker compose exec app alembic upgrade head

# 4. 확인
curl http://localhost:8000/health
# → {"status": "ok", "version": "0.2.0"}
```

### 로컬 직접 실행 (MariaDB는 별도 기동 필요)

```bash
# 백엔드
pip install -r backend/requirements.txt
cd backend && alembic upgrade head
cd backend && python run.py
# → http://localhost:8000 / Swagger: http://localhost:8000/docs

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev
# → http://localhost:5173/demo.html  (AI 테스트 페이지)
# → http://localhost:5173/admin.html (관리자 대시보드)
```

---

## 3. 환경변수 (.env)

| 변수명 | 필수 | 설명 |
|--------|------|------|
| `GEMINI_API_KEY` | ✅ | Google AI Studio에서 발급 |
| `JWT_SECRET` | ✅ | 맘아이 메인 서버와 공유하는 HS256 시크릿 |
| `ADMIN_API_KEY` | ✅ | X-API-Key 헤더값 (임의 문자열, 직접 설정) |
| `DATABASE_URL` | ✅ | MariaDB 연결 문자열 |
| `DB_ROOT_PASSWORD` | ✅ | MariaDB root 비밀번호 |
| `DB_NAME` | ✅ | DB 이름 |
| `DB_USER` | ✅ | DB 유저명 |
| `DB_PASSWORD` | ✅ | DB 비밀번호 |

> 도커 실행 시 `DATABASE_URL`은 `docker-compose.yml`이 컨테이너 내부 주소로 오버라이드.

---

## 4. 패키지 의존성

### 백엔드 (`backend/requirements.txt`)

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `fastapi` | 0.135.3 | 웹 프레임워크 |
| `uvicorn` | 0.44.0 | ASGI 서버 |
| `pydantic` | 2.13.0 | 요청/응답 유효성 검사 |
| `pydantic-settings` | 2.13.1 | `.env` 로드 |
| `python-jose` | 3.3.0 | JWT 검증 |
| `google-genai` | latest | Gemini 비동기 클라이언트 |
| `APScheduler` | 3.11.2 | rolling 삭제 스케줄러 |
| `SQLAlchemy` | 2.0.49 | ORM |
| `alembic` | 1.18.4 | DB 마이그레이션 |
| `pymysql` | 1.1.0 | MariaDB 드라이버 |
| `pytest` | 7.4.2 | 테스트 |

### 프론트엔드 (`frontend/package.json`)

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `react` | ^19.2.5 | UI 프레임워크 |
| `react-dom` | ^19.2.5 | DOM 렌더링 |
| `vite` | ^8.0.4 | 빌드 도구 (멀티 페이지) |
| `typescript` | ~6.0.2 | 타입 체크 |
| `chart.js` + `react-chartjs-2` | ^4.5.1 / ^5.3.1 | 수면 차트 |
| `html2canvas` | ^1.4.1 | PDF 스크린샷 캡처 |
| `jspdf` | ^4.2.1 | PDF 생성 |
| `lucide-react` | ^1.11.0 | 아이콘 |

---

## 5. 프로젝트 구조

```
mom-i/
├── .env                        ← 환경변수 (커밋 금지)
├── .env.example                ← 팀원 온보딩용 샘플
├── docker-compose.yml
├── backend/
│   ├── run.py
│   ├── requirements.txt
│   ├── alembic/
│   └── app/
│       ├── main.py
│       ├── core/               # config.py, security.py
│       ├── domain/report/      # entity.py, schemas.py
│       ├── application/report/ # report_service.py
│       ├── infrastructure/
│       │   ├── database/       # session.py, repository/report_repo.py
│       │   ├── llm/            # gemini_client.py, prompts/ (6개 파일)
│       │   ├── emtake/         # client.py (EMTAKE relay API 호출)
│       │   └── scheduler.py
│       └── interfaces/api/v1/  # report_api.py, admin_api.py
├── frontend/
│   ├── demo.html               ← Vite 진입점 (AI 테스트 페이지)
│   ├── admin.html              ← Vite 진입점 (관리자 대시보드)
│   ├── vite.config.ts          ← 멀티 페이지 빌드 설정
│   ├── public/                 # favicon, 광고 이미지 (ad-momi-*.png|jpg)
│   └── src/
│       ├── main-demo.tsx       ← Demo 진입점
│       ├── main-admin.tsx      ← Admin 진입점
│       ├── pages/
│       │   ├── Demo.tsx        ← 리포트 생성 테스트, PDF 다운로드
│       │   └── Admin.tsx       ← 기기 목록, 리포트 뷰어, PDF 다운로드
│       └── components/
│           ├── ReportView.tsx  ← 공유 리포트 렌더링 컴포넌트
│           ├── AdBanner.tsx    ← 광고 배너
│           └── charts/         # ChartSetup.ts (Chart.js 등록)
└── docs/
```

---

## 6. API 테스트

### curl — 리포트 생성

```bash
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-local-key" \
  -d '{
    "ser_no": "MT-00123",
    "baby_age_months": 8,
    "week_start": "2026-04-07",
    "sleep": [
      {"date": "2026-04-07", "sleep_min": 570, "restless_min": 22, "wakeup_count": 2},
      {"date": "2026-04-08", "sleep_min": 540, "restless_min": 30, "wakeup_count": 3},
      {"date": "2026-04-09", "sleep_min": 600, "restless_min": 15, "wakeup_count": 1},
      {"date": "2026-04-10", "sleep_min": 510, "restless_min": 35, "wakeup_count": 4},
      {"date": "2026-04-11", "sleep_min": 580, "restless_min": 20, "wakeup_count": 2},
      {"date": "2026-04-12", "sleep_min": 560, "restless_min": 25, "wakeup_count": 2},
      {"date": "2026-04-13", "sleep_min": 590, "restless_min": 18, "wakeup_count": 1}
    ],
    "environment": {
      "temp_avg": 21.5, "temp_max": 24.0, "temp_min": 19.0,
      "db_max": 62, "db_avg": 48,
      "humidity_avg": 50.0, "humidity_min": 42.0, "humidity_max": 58.0,
      "bright_avg": 3.0, "bright_min": 0.0, "bright_max": 8.0
    },
    "events": {"cry_count": 3, "leave_count": 1},
    "breath": {"breath_min": 22, "breath_max": 38, "breath_avg": 28},
    "body_temp": {"body_temp_min": 0.1, "body_temp_max": 0.7, "body_temp_avg": 0.3},
    "monthly": {"month_sleep_h": 9.2, "month_restless_h": 0.5, "week_sleep_h": 9.5, "week_restless_h": 0.4}
  }'
```

> **주의**: `body_temp`는 절대 체온이 아닌 **델타값(기준치 대비 상승분, °C)**. EMTAKE `Temp` 원시값 그대로 사용.  
> `humidity_*`, `bright_*`, `wakeup_count`는 optional — 없으면 null로 전달해도 됨.

### curl — 관리자

```bash
# 기기 목록
curl -H "X-API-Key: dev-local-key" http://localhost:8000/api/v1/admin/devices

# 기기별 리포트
curl -H "X-API-Key: dev-local-key" http://localhost:8000/api/v1/admin/devices/MT-00123/reports

# 전체 통계
curl -H "X-API-Key: dev-local-key" http://localhost:8000/api/v1/admin/stats
```

---

## 7. 알려진 이슈

| 항목 | 내용 |
|------|------|
| `GEMINI_API_KEY` 미설정 | 서버 기동은 되지만 `/generate` 호출 시 AI 단계에서 오류 |
| `DATABASE_URL` 미설정 | 서버 기동 시 DB 연결 오류 발생 (빈 문자열 기본값) |
| CORS | `allow_origins=["*"]` — 운영 배포 전 도메인 제한 필요 |
