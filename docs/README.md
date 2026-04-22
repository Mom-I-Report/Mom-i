# Mom-i 리포트 서버 — 문서 인덱스

> 브랜치: `feat/noh` | 최종 갱신: 2026-04-19

이 폴더는 맘아이 리포트 서버의 모든 설계·개발·운영 문서를 관리합니다.
새로운 팀원이라면 **아래 순서대로** 읽으세요.

---

## 빠른 시작

```
1. dev-environment.md   → 로컬 환경 세팅
2. research.md          → 시스템 전체 구조 파악
3. plan.md              → 현재 개발 상황 및 남은 작업 확인
```

---

## 현행 문서

| 파일 | 설명 | 마지막 갱신 |
|------|------|------------|
| [plan.md](./plan.md) | 전체 개발 계획 (P0~P3 우선순위, 미완료 작업 목록) | 2026-04-19 |
| [research.md](./research.md) | 리포트 생성 시스템 심층 분석 (전 레이어 코드 기준) | 2026-04-19 |
| [dev-environment.md](./dev-environment.md) | 로컬 개발 환경 세팅, 패키지 목록, API 테스트 방법 | 2026-04-19 |
| [meeting-report-decisions-2026-04-19.md](./meeting-report-decisions-2026-04-19.md) | 리포트 UI 구현을 위한 팀 결정 사항 회의 자료 | 2026-04-19 |

---

## 하위 폴더

| 폴더 | 설명 |
|------|------|
| [reference/](./reference/) | 외부 참고 자료 (EMTAKE 프로토콜, Claude Code 가이드 등) |
| [work-logs/](./work-logs/) | 작업자별 작업 일지 |
| [archive/](./archive/) | 폐기된 구버전 문서 |
| [image/](./image/) | UI 목업 스크린샷 (Notion 리포트 화면) |

---

## 시스템 개요

```
맘아이 서버  →  POST /api/v1/report/generate  →  리포트 JSON 반환
앱 (사용자)  →  GET  /api/v1/report/history/{ser_no}  →  최근 3주치
```

- **스택:** FastAPI + SQLAlchemy (SQLite/MySQL) + Gemini 2.5 Flash
- **DB:** Weekly_Data, Generated_Reports, ETF 3개 테이블
- **AI:** Gemini 2.5 Flash — async, 재시도(최대 3회), 5섹션 검증, Thinking Budget 1024

---

## 팀 역할

| 역할 | 담당 |
|------|------|
| AI 리포트 (비용 절감·신뢰성) | 노호종 |
| 도메인 지식 (소아과 기준·점수 산식) | 담당자 |
| 백엔드 공통 (인프라·ETF·배포) | 담당자 |

---

## 현재 미결 사항 (팀 합의 필요)

> 상세 내용 → [meeting-report-decisions-2026-04-19.md](./meeting-report-decisions-2026-04-19.md)

1. **수면 점수 산식** — 히스토리·Best/Worst·일별 점수 전부의 선결 조건
2. **취침/기상 시각** — EMTAKE에서 수신 가능한지 확인 필요
3. **AI 출력 형식** — 텍스트(현재) vs 구조화 JSON 결정 (앱팀 협의)
4. **리포트 보존 기간** — 현재 3주, UI는 6주 표시
5. **발달 가이드** — 고정 콘텐츠 vs Gemini 생성

---

## 문서 작성 규칙

- 파일명: `kebab-case.md` (한글 파일명 사용 금지)
- 날짜 포함 문서: `{type}-YYYY-MM-DD.md` 형식
- 폐기 문서: `archive/` 이동 후 상단에 `> [DEPRECATED]` 표시
- 작업 일지: `work-logs/YYYY-MM-DD-{author}.md` 형식
