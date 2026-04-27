# docs/noh — 노호종 작업 문서 인덱스

> AI 리포트 서버 담당 (feat/noh 브랜치)

---

## 문서 목록

| 파일 | 날짜 | 분류 | 한줄 요약 |
|------|------|------|----------|
| [meeting-report-decisions-2026-04-19.md](./meeting-report-decisions-2026-04-19.md) | 04-19 | 회의 | UI 목업 vs API 갭 분석 + 미결 의제 5개 |
| [emtake-data-request-2026-04-20.md](./emtake-data-request-2026-04-20.md) | 04-20 | 협의 | 엠테이크 측 데이터 추가 요청 공문 초안 |
| [prompt-context-engineering-2026-04-26.md](./prompt-context-engineering-2026-04-26.md) | 04-26 | 작업 | 프롬프트 6파일 분리 및 Gemini 컨텍스트 엔지니어링 |
| [domain-knowledge-code-mapping-2026-04-26.md](./domain-knowledge-code-mapping-2026-04-26.md) | 04-26 | 분석 | 도메인 지식(knowledge.md) → 코드 반영 매핑 + 버그 수정 |
| [service-readiness-checklist-2026-04-26.md](./service-readiness-checklist-2026-04-26.md) | 04-26 | 체크 | 서비스 전 블로킹 이슈 + 환경설정 가이드 |
| [frontend-render-unification-2026-04-27.md](./frontend-render-unification-2026-04-27.md) | 04-27 | 작업 | demo/admin 렌더링 통일 (공유 JS·CSS 추출) + 버그 수정 |
| [report-delivery-options-2026-04-27.md](./report-delivery-options-2026-04-27.md) | 04-27 | 협의 | 앱팀 협의용 리포트 전달 방식 4가지 옵션 비교 |
| [system-flow-2026-04-27.md](./system-flow-2026-04-27.md) | 04-27 | 설계 | 전체 시스템 플로우 다이어그램 (코드 기준) |

---

## 의제 처리 현황 (meeting-report-decisions 기준)

| 의제 | 내용 | 상태 |
|------|------|------|
| #1 수면 점수 산식 | 점수/등급/Best·Worst 산식 결정 | ⏳ 미결 |
| #2 취침/기상 시각 | EMTAKE 전송 가능 여부 확인 | ⏳ 엠테이크 확인 필요 |
| #3 AI 출력 형식 | 텍스트 → 구조화 JSON | ✅ 완료 (B안 구현) |
| #4 발달 가이드 | Gemini 생성 vs 고정 콘텐츠 | ✅ 완료 (Gemini 생성, `age_kick` 필드) |
| #5 보존 기간 | 3주 vs 6주 | ✅ 완료 (Generated_Reports 5주 / Weekly_Data 12주) |

---

## 서비스 준비 현황 (service-readiness-checklist 기준)

| 항목 | 상태 |
|------|------|
| 릴레이 서버 스키마 합의 | ⏳ 미완 |
| `.env` 실제 값 채우기 | ⏳ 미완 |
| DB 테이블 생성 (alembic) | ⏳ 미완 |
| CORS 도메인 제한 | 🟡 운영 전 처리 |
| 스케줄러 로그 오류 | ✅ 수정 완료 (04-26) |
| sleep_guide null 버그 | ✅ 수정 완료 (04-26) |
| demo/admin 렌더링 통일 | ✅ 완료 (04-27) |
| Gemini SDK 전환 (google-genai) | ✅ 완료 (04-27) |
| 관리자 기기 API 추가 | ✅ 완료 (04-27) |
| 리포트 전달 방식 앱팀 협의 | ⏳ 협의 필요 |
