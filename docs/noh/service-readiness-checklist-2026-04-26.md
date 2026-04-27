# 서비스 준비 체크리스트

날짜: 2026-04-26  
브랜치: feat/noh  
목적: 릴레이 서버(맘아이 메인 서버) 연동 후 서비스 가능 여부 점검

---

## 요약

| 구분 | 항목 | 상태 |
|------|------|------|
| 🔴 블로킹 | 릴레이 서버 ↔ 리포트 서버 스키마 합의 | 미완 |
| 🔴 블로킹 | `.env` 실제 값 채우기 (키 3개 + DB 4개) | 미완 |
| 🔴 블로킹 | DB 테이블 생성 (docker compose up 또는 alembic) | 미완 |
| 🟡 운영 전 | CORS `allow_origins=["*"]` → 도메인 제한 | 코드 수정 필요 |
| 🟡 운영 전 | 스케줄러 로그 메시지 오류 | 코드 수정 필요 |
| 🟢 언젠가 | `google-generativeai` deprecated → `google-genai` 마이그레이션 | 당장 서비스 가능 |
| 🟢 언젠가 | `on_event("startup")` deprecated → `lifespan` 방식 전환 | 당장 서비스 가능 |
| ✅ 완료 | `sleep_guide: null` 처리 버그 수정 | 오늘 수정 완료 |

---

## 🔴 블로킹 항목

### 1. 릴레이 서버 ↔ 리포트 서버 스키마 합의

맘아이 메인 서버(릴레이)가 `POST /api/v1/reports/generate`를 호출할 때 아래 JSON을 정확하게 보내야 한다.  
**EMTAKE 원시 데이터 → 아래 포맷 변환은 맘아이 서버 담당** (schemas.py에 명시).

#### 요청 스키마 (`GenerateReportRequest`)

```json
{
  "ser_no": "ABC123",
  "baby_age_months": 8,
  "week_start": "2026-04-21",
  "sleep": [
    { "date": "2026-04-21", "sleep_min": 560, "restless_min": 25 },
    { "date": "2026-04-22", "sleep_min": 480, "restless_min": 30 },
    { "date": "2026-04-23", "sleep_min": 530, "restless_min": 20 },
    { "date": "2026-04-24", "sleep_min": 510, "restless_min": 35 },
    { "date": "2026-04-25", "sleep_min": 490, "restless_min": 40 },
    { "date": "2026-04-26", "sleep_min": 520, "restless_min": 28 },
    { "date": "2026-04-27", "sleep_min": 550, "restless_min": 22 }
  ],
  "environment": {
    "temp_avg": 21.5,
    "temp_max": 23.0,
    "temp_min": 20.0,
    "db_max": 58,
    "db_avg": 42
  },
  "breath": {
    "breath_min": 22,
    "breath_max": 38,
    "breath_avg": 30
  },
  "body_temp": {
    "body_temp_min": 36.5,
    "body_temp_max": 37.2,
    "body_temp_avg": 36.8
  },
  "monthly": {
    "month_sleep_h": 10.5,
    "month_restless_h": 0.6
  },
  "events": {
    "cry_count": 3,
    "leave_count": 1
  }
}
```

#### 필드 설명 및 변환 규칙

| 필드 | 타입 | 단위 | EMTAKE 원본 | 변환 책임 |
|------|------|------|------------|----------|
| `ser_no` | string | - | 기기 시리얼 | 맘아이 서버 |
| `baby_age_months` | int | 개월 | 생년월일 → 계산 | 맘아이 서버 |
| `week_start` | date | - | 반드시 월요일 | 맘아이 서버 |
| `sleep[].sleep_min` | int | 분 | EMTAKE `day_gs` "4h50m" | 맘아이 서버 |
| `sleep[].restless_min` | int | 분 | EMTAKE `day_pr` | 맘아이 서버 |
| `environment.temp_avg/max/min` | float | °C | EMTAKE `IndoorTemp` | 맘아이 서버 |
| `environment.db_max/avg` | int | dB | EMTAKE `dB` | 맘아이 서버 |
| `breath.breath_*` | int | 회/분 | EMTAKE `Breath` | 맘아이 서버 |
| `body_temp.*` | float | °C | EMTAKE `Temp` | 맘아이 서버 |
| `monthly.month_sleep_h` | float | 시간 | EMTAKE `month_gs` "3h45m" | 맘아이 서버 |
| `monthly.month_restless_h` | float | 시간 | EMTAKE `month_pr` | 맘아이 서버 |
| `events.cry_count` | int | 횟수 | 울음 감지 이벤트 | 맘아이 서버 |
| `events.leave_count` | int | 횟수 | 카메라 이탈 이벤트 | 맘아이 서버 |

**주의**: `sleep` 배열은 반드시 7개. 7개 미만이면 422 자동 반환.

#### 인증 헤더

```
X-API-Key: {ADMIN_API_KEY 값}
Content-Type: application/json
```

#### 응답 구조 (`GenerateReportResponse`)

```json
{
  "ser_no": "ABC123",
  "week_start": "2026-04-21",
  "week_label": "2026년 4월 4주차",
  "generated_at": "2026-04-26T14:30:00",
  "summary": {
    "avg_sleep_h": 8.0,
    "avg_restless_min": 29,
    "cry_count": 3,
    "leave_count": 1,
    "temp_avg": 21.5,
    "db_max": 58,
    "month_sleep_h": 10.5,
    "month_restless_h": 0.6
  },
  "breath": {
    "breath_min": 22,
    "breath_max": 38,
    "breath_avg": 30,
    "is_normal": true,
    "normal_range": "20~40회/분 (생후 12개월 이하 기준)"
  },
  "body_temp": {
    "body_temp_min": 36.5,
    "body_temp_max": 37.2,
    "body_temp_avg": 36.8,
    "status": "정상"
  },
  "daily": [
    { "date": "2026-04-21", "day": "월", "sleep_h": 9.3, "restless_min": 25 }
  ],
  "trend": {
    "sleep_vs_last_week": 0.3,
    "restless_vs_last_week": -5,
    "cry_vs_last_week": -1,
    "breath_vs_last_week": 0,
    "body_temp_vs_last_week": 0.1
  },
  "ai_comment": [
    { "type": "good", "icon": "😴", "title": "수면 안정적", "text": "이번 주 수면 시간이..." }
  ],
  "sleep_guide": {
    "method_name": "퍼버법",
    "title": "시도해볼 수 있는 수면 가이드: 퍼버법",
    "reason": "이번 주 뒤척임이 평균 29분으로...",
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

**참고**:
- `trend`: 이전 주 데이터 없으면 `null`
- `sleep_guide`: 0~2개월 아기이면 `null`
- `age_kick`: 일반적으로 항상 있음

---

### 2. `.env` 실제 값 채우기

`.env.example`을 복사해 `.env`를 만들고 아래 7개 값을 채운다.

```bash
cp .env.example .env
```

```dotenv
# ── DB (docker-compose MariaDB 컨테이너) ──────────────────────────────────────
DB_ROOT_PASSWORD="실제_루트_비밀번호"
DB_NAME="momi_db"
DB_USER="momi_user"
DB_PASSWORD="실제_DB_비밀번호"

# ── App ───────────────────────────────────────────────────────────────────────
GEMINI_API_KEY="구글_AI_스튜디오_발급_키"          # https://aistudio.google.com
DATABASE_URL="mysql+pymysql://momi_user:비밀번호@localhost:3306/momi_db"

JWT_SECRET="맘아이_메인서버와_동일한_HS256_시크릿"  # ← 반드시 메인 서버 팀과 공유
ADMIN_API_KEY="릴레이서버가_X-API-Key로_보낼_임의_문자열"  # ← 릴레이 서버 팀과 공유
```

**체크포인트**:
- `JWT_SECRET`: 맘아이 메인 서버가 JWT를 발급할 때 쓰는 시크릿과 **완전히 동일**해야 함. 다르면 앱 로그인 후 리포트 조회 시 401.
- `ADMIN_API_KEY`: 릴레이 서버가 `POST /generate` 호출 시 헤더에 넣는 값. 다르면 403.
- `GEMINI_API_KEY`: Google AI Studio → API Keys에서 생성. 모델명 `gemini-3-flash-preview` 접근 권한 확인 필요.

---

### 3. DB 테이블 생성

#### 방법 A — Docker Compose (권장, 운영)

```bash
# 프로젝트 루트에서
docker compose up -d

# 컨테이너 내부에서 마이그레이션 (최초 1회)
docker compose exec app alembic revision --autogenerate -m "initial"
docker compose exec app alembic upgrade head
```

**참고**: `create_tables()`가 startup에서 자동 실행되므로 Alembic 없이도 테이블이 생성됨.  
그러나 이후 컬럼 추가/변경 시 Alembic 없으면 `ALTER TABLE`이 반영되지 않으므로 처음부터 Alembic으로 관리 권장.

#### 방법 B — 로컬 직접 실행 (개발)

```bash
# MariaDB가 이미 실행 중이어야 함
cd backend && alembic revision --autogenerate -m "initial"
cd backend && alembic upgrade head
cd backend && python run.py  # http://localhost:8000
```

**현재 상태**: `alembic/versions/` 폴더가 비어있음 → `revision --autogenerate`를 한 번도 실행하지 않은 상태.  
SQLite 로컬 개발 시에는 `create_tables()` 자동 생성으로 OK. MariaDB로 가면 반드시 Alembic 실행 필요.

---

## 🟡 운영 전 처리 권장

### 4. CORS 도메인 제한

**파일**: `backend/app/main.py:27`

```python
# 현재 (전체 허용)
allow_origins=["*"],

# 운영 시 변경
allow_origins=["https://앱_실제_도메인"],
```

앱이 웹뷰 기반이라면 실제 WebView 도메인을 명시. 네이티브 앱만 호출한다면 `["*"]`도 무방하지만 보안상 좁히는 것이 원칙.

---

### 5. 스케줄러 로그 메시지 오류

**파일**: `backend/app/infrastructure/scheduler.py:21`

```python
# 현재 (잘못된 메시지)
logger.info("[스케줄러] 오래된 데이터 삭제 완료 (3주 초과)")

# 실제 삭제 기준은 (report_repo.py:268-274)
#   Generated_Reports: 5주 초과
#   Weekly_Data:      12주 초과
```

로그만 보고 동작을 오해할 수 있어 수정 권장.

```python
logger.info("[스케줄러] 오래된 데이터 삭제 완료 (Generated_Reports 5주 초과 / Weekly_Data 12주 초과)")
```

---

## 🟢 당장 서비스 가능 (언젠가 처리)

### 6. `google-generativeai` → `google-genai` 마이그레이션

**현재**: `requirements.txt`에 `google-generativeai==0.8.6`  
**이슈**: 구글이 `google-generativeai` 패키지를 deprecated하고 `google-genai`로 통합 중. FutureWarning 발생.  
**현재 영향**: 서비스는 정상 작동. 단, 구글이 완전 삭제하면 오류 발생.

마이그레이션 시 변경 범위:
- `requirements.txt`: `google-generativeai` → `google-genai`
- `gemini_client.py:15`: `import google.generativeai as genai` → `from google import genai`
- API 초기화 방식 변경 필요 (genai.Client() 방식)

---

### 7. `on_event("startup")` → `lifespan` 방식 전환

**파일**: `backend/app/main.py:34`

```python
# 현재 (deprecated)
@app.on_event("startup")
def on_startup():
    create_tables()
    start_scheduler()
```

FastAPI 0.93+ 부터 `on_event`가 deprecated. 경고만 출력되고 서비스는 작동함.

```python
# 변경 방향
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    start_scheduler()
    yield

app = FastAPI(..., lifespan=lifespan)
```

---

## ✅ 이미 완료

| 항목 | 내용 |
|------|------|
| sleep_guide null 처리 버그 수정 | 0~2개월 아기 시 `SleepGuide(**None)` → `TypeError` 수정 완료 (2026-04-26) |
| 프롬프트 6파일 분리 | system / knowledge / age_policy / reasoning / output_format / input_template |
| kick_action 필드 추가 | SleepGuide에 추가, demo.html 렌더링 추가 |
| Gemini 모델 변경 | `gemini-2.5-flash` → `gemini-3-flash-preview` |
| AAP 기준 코드 반영 | 수면시간·호흡수·체온·뒤척임 판정 모두 코드에서 직접 계산 |
| 캐시 로직 | 동일 주차 재호출 시 Gemini 재호출 없이 DB 캐시 반환 |
| rolling 삭제 | 매주 월요일 10:00 KST 자동 삭제 (Generated_Reports 5주 / Weekly_Data 12주) |
| 인증 구조 | X-API-Key (서버→서버) + JWT Bearer (앱→서버) 완성 |

---

## 서비스 시작 순서

```
1. .env 파일 값 채우기 (JWT_SECRET, ADMIN_API_KEY 릴레이 서버 팀과 공유)
2. 릴레이 서버 팀과 스키마 합의 (요청 JSON 필드 목록 공유)
3. docker compose up -d
4. docker compose exec app alembic revision --autogenerate -m "initial"
5. docker compose exec app alembic upgrade head
6. POST /api/v1/reports/generate 호출 테스트 (Swagger: http://localhost:8000/docs)
7. 앱 JWT 토큰으로 GET /api/v1/reports 호출 테스트
```
