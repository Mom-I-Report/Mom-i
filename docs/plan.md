# 맘아이 리포트 서버 — 개발 플랜

> 최종 갱신: 2026-04-27  
> 기준 브랜치: `feat/noh`

---

## 1. 구현 완료

| 항목 | 내용 |
|------|------|
| 리포트 생성 파이프라인 | 6단계 (upsert→캐시→조회→집계→Gemini→저장) |
| 인증/인가 | X-API-Key (리포트 생성·관리자), JWT Bearer (앱) |
| 앱 리포트 조회 | `GET /api/v1/reports`, `GET /api/v1/reports/{id}` (JWT 기반 ser_no 격리) |
| 관리자 API | `/stats`, `/devices`, `/devices/{ser_no}/reports` |
| Gemini SDK | `google-genai` 전환 완료 (`_client.aio.models.generate_content`) |
| 프롬프트 | 6개 파일 분리 (system·knowledge·age_policy·reasoning·output_format·input_template) |
| AI 출력 구조 | 구조화 JSON (`ai_comment`, `sleep_guide`, `age_kick`) |
| 스케줄러 | 매주 월 10:00 KST rolling 삭제 (Weekly_Data 12주, Generated_Reports 5주) |
| 로깅 | `main.py` 전역 포맷 설정 완료 |
| health 엔드포인트 | `GET /health` |
| 프론트엔드 렌더링 통일 | `report-renderer.js`, `report.css` 공유 모듈 |
| `.gitignore` | Python·Node·log 항목 보완 |

---

## 2. 미완료 — 남은 작업

### 🔴 서비스 전 필수

| 항목 | 내용 |
|------|------|
| 릴레이 서버 스키마 합의 | EMTAKE `day_pr` 의미 (낮잠 vs 뒤척임), `cry_count` 출처 확인 필요 |
| `.env` 실제 값 채우기 | `GEMINI_API_KEY`, `JWT_SECRET`, `ADMIN_API_KEY`, DB 접속 정보 |
| DB 마이그레이션 | `alembic upgrade head` 실행 (MariaDB 컨테이너 기동 후) |
| 리포트 전달 방식 협의 | 앱팀과 WebView vs 네이티브 렌더링 방향 결정 필요 |

### 🟡 운영 전 처리

| 항목 | 내용 |
|------|------|
| CORS 도메인 제한 | `allow_origins=["*"]` → 실제 앱 도메인으로 교체 |
| pytest 테스트 | `test_report_service.py` (캐시 히트·trend None·3주 흐름) 최소 커버 |

### 🟢 선택적 개선

| 항목 | 내용 |
|------|------|
| async SQLAlchemy | sync 세션 → `AsyncSession` 전환 (MariaDB 운영 시 이벤트 루프 블로킹 방지) |
| 토큰 사용량 DB 저장 | 현재 로그만 기록, 기기별 비용 추적 필요 시 컬럼 추가 |

---

## 3. API 전체 목록

| 메서드 | 경로 | 인증 | 상태 |
|--------|------|------|------|
| `POST` | `/api/v1/reports/generate` | X-API-Key | ✅ |
| `GET`  | `/api/v1/reports` | JWT | ✅ |
| `GET`  | `/api/v1/reports/{report_id}` | JWT | ✅ |
| `GET`  | `/api/v1/admin/stats` | X-API-Key | ✅ |
| `GET`  | `/api/v1/admin/devices` | X-API-Key | ✅ |
| `GET`  | `/api/v1/admin/devices/{ser_no}/reports` | X-API-Key | ✅ |
| `GET`  | `/health` | 없음 | ✅ |

---

## 4. DB 테이블

| 테이블 | 역할 | 보존 기간 |
|--------|------|---------|
| `Weekly_Data` | 주간 원본 (AI 트렌드 컨텍스트) | 12주 rolling |
| `Generated_Reports` | 생성된 리포트 JSON (앱 열람) | 5주 rolling |
