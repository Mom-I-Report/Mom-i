# docs/noh — 노호종 작업 문서 인덱스

> AI 리포트 서버 담당 (feat/noh 브랜치)

---

## 작업 일지

| 파일 | 날짜 | 한줄 요약 |
|------|------|----------|
| [260426.md](./260426.md) | 04-26 | 프롬프트 6파일 분리, 도메인 지식 코드 매핑, kick_action 추가, 버그 수정 |
| [260427.md](./260427.md) | 04-27 | 프론트엔드 렌더링 통일, 관리자 기기 API, Gemini SDK 전환 |
| [260511.md](./260511.md) | 05-11 | 스키마 확장, EMTAKE 클라이언트 구현, AI 출력 필드 추가, 지식 보강, 프론트엔드 개편 |
| [260512.md](./260512.md) | 05-12 | 릴레이 데이터 전체 통합(Humidity/Bright/sessions), Gemini 프롬프트 강화, CORS 버그 수정 |

---

## 참고 문서

| 파일 | 날짜 | 분류 | 한줄 요약 |
|------|------|------|----------|
| [meeting-report-decisions-2026-04-19.md](./meeting-report-decisions-2026-04-19.md) | 04-19 | 회의 | UI 목업 vs API 갭 분석 + 미결 의제 5개 |
| [emtake-data-request-2026-04-20.md](./emtake-data-request-2026-04-20.md) | 04-20 | 협의 | 엠테이크 측 데이터 추가 요청 공문 초안 |
| [service-readiness-checklist-2026-04-26.md](./service-readiness-checklist-2026-04-26.md) | 04-26 | 체크 | 서비스 전 블로킹 이슈 + 환경설정 가이드 |
| [report-delivery-options-2026-04-27.md](./report-delivery-options-2026-04-27.md) | 04-27 | 협의 | 앱팀 협의용 리포트 전달 방식 4가지 옵션 비교 |
| [system-flow-2026-04-27.md](./system-flow-2026-04-27.md) | 04-27 | 설계 | 전체 시스템 플로우 다이어그램 (코드 기준) |

---

## 의제 처리 현황 (meeting-report-decisions 기준)

| 의제 | 내용 | 상태 |
|------|------|------|
| #1 수면 점수 산식 | 점수/등급/Best·Worst 산식 결정 | ⏳ 미결 |
| #2 취침/기상 시각 | EMTAKE sessions[] 필드로 일부 확보 (start/end) | 🟡 부분 해결 |
| #3 AI 출력 형식 | 텍스트 → 구조화 JSON | ✅ 완료 (B안 구현) |
| #4 발달 가이드 | Gemini 생성 vs 고정 콘텐츠 | ✅ 완료 (Gemini 생성, `age_kick` 필드) |
| #5 보존 기간 | 3주 vs 6주 | ✅ 완료 (Generated_Reports 5주 / Weekly_Data 12주) |

---

## 서비스 준비 현황

| 항목 | 상태 |
|------|------|
| 릴레이 서버 스키마 합의 | 🟡 진행 중 (sessions, Humidity, Bright 추가 반영 완료) |
| `.env` 실제 값 채우기 | ⏳ 미완 |
| DB 테이블 생성 (alembic) | ⏳ 미완 |
| CORS 도메인 제한 | ✅ credentials 버그 수정 완료 (05-12) / 운영 시 origins 제한 필요 |
| 스케줄러 로그 오류 | ✅ 수정 완료 (05-12) |
| sleep_guide null 버그 | ✅ 수정 완료 (04-26) |
| 체온 판정 기준 오류 (절대값→델타값) | ✅ 수정 완료 (04-26) |
| 관리자 기기 API 추가 | ✅ 완료 (04-27) |
| Gemini SDK 전환 (google-genai) | ✅ 완료 (04-27) |
| EMTAKE 전체 필드 통합 | ✅ 완료 (05-12) |
| 프론트엔드 React/Vite 전환 | ✅ 완료 (05-11~12) |
| 리포트 전달 방식 앱팀 협의 | ⏳ 협의 필요 |
