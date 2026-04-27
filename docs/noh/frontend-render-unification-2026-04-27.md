# 프론트엔드 렌더링 통일 — 2026-04-27

## 배경

`demo.html`(테스트용)과 `admin.html`(관리자용)이 동일한 `report_json`을 렌더링하는데  
각자 별도의 CSS·JS를 갖고 있어 항목 수, 레이아웃이 달랐음.

| 항목 | 통일 전 |
|------|---------|
| demo.html 주간요약 항목 수 | 3개 (수면·뒤척임·울음) |
| admin.html 주간요약 항목 수 | 5개 (수면·뒤척임·울음·호흡·체온) |

두 페이지 모두 DB에 저장된 동일 JSON을 표시하므로 렌더링이 일치해야 함.

---

## 해결 방법

공유 모듈을 `frontend/public/`에 추출 (Vite가 변환하지 않고 그대로 서빙).

```
frontend/public/
├── report-renderer.js   ← renderReportBody(container, rj, opts)
└── report.css           ← 공유 스타일
```

---

## renderReportBody API

```javascript
renderReportBody(container, rj, opts)
// container : DOM 요소 (innerHTML 교체됨)
// rj        : report_json (API 응답 / DB 저장 형식 동일)
// opts      : { radarId, barId, showTrend }
//   showTrend: true → 관리자용 전주 대비 뱃지 표시
```

렌더링 섹션 순서:
1. 주간 요약 (레이더 차트 + stat-stack 5행)
2. 일별 수면 (막대+꺾은선 차트, daily 있을 때만)
3. AI 솔루션 (`sleep_guide`, kick_action 포함)
4. AI 코멘트 (`ai_comment`)
5. 월령 키워드 (`age_kick`)

---

## 수정된 버그

| 버그 | 원인 | 수정 |
|------|------|------|
| `0h`, `0분`, `0회` 뱃지 표시 | trendBadge에서 `val === 0` 미처리 | `|| val === 0` 조건 추가 |
| kick_action 미표시 | 통일 작업 중 렌더링 블록 누락 | kick_action 조건부 렌더링 추가 |

---

## 페이지별 차이점

| 항목 | demo.html | admin.html |
|------|-----------|-----------|
| showTrend | false | true |
| radarId | `radarChart` | `adminRadarChart` |
| barId | `dailyBarChart` | `adminBarChart` |
| 탭 전환 | 없음 | 최근 3주 탭 (`switchTab()`) |
