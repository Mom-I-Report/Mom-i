# 리포트 전달 방식 협의 문서

> 맘아이 앱팀과 협의를 위한 정리  
> 작성일: 2026-04-27

---

## 배경

리포트 서버는 Gemini AI로 분석한 주간 수면 리포트를 생성해 DB에 보관합니다.  
현재 API는 **JSON**을 리턴하며, 앱이 이 데이터를 어떻게 표시할지 협의가 필요합니다.

---

## 현재 리포트 JSON 구조

```json
{
  "ser_no": "기기 시리얼",
  "week_start": "2026-04-14",
  "week_label": "2026년 4월 2주차",
  "summary": { "avg_sleep_h": 11.5, "avg_restless_min": 25, "cry_count": 5, ... },
  "breath": { "breath_avg": 30, "is_normal": true, ... },
  "body_temp": { "body_temp_avg": 36.7, "status": "정상", ... },
  "daily": [{ "day": "월", "sleep_h": 11.5, "restless_min": 25 }, ...],
  "trend": { "sleep_vs_last_week": 0.5, "restless_vs_last_week": -5, ... },
  "ai_comment": [{ "type": "good", "icon": "😴", "title": "...", "text": "..." }],
  "sleep_guide": { "method_name": "퍼버법", "title": "...", "reason": "...", "steps": [...] },
  "age_kick": { "title": "8개월 분리불안", "text": "...", "is_wonder_weeks": true }
}
```

---

## 전달 방식 옵션 비교

### Option A — WebView + URL ⭐ 권장

**흐름**
```
앱 → GET /api/v1/reports/{id}?format=html
   → 서버가 JWT 검증 후 HTML 렌더링해서 리턴
   → 앱 WebView에 표시
```

**장점**
- 앱 개발 공수 최소 (WebView 1개)
- 리포트 디자인 변경 시 앱 업데이트 불필요
- PDF 저장 버튼도 WebView 안에서 처리 가능
- 현재 서버 HTML 코드 거의 그대로 활용

**단점**
- 인터넷 연결 필수
- WebView 내 폰트·애니메이션 일부 제약 가능성

**앱팀 작업량**  
`webView.load(url)` 한 줄 + JWT 토큰 헤더 전달

---

### Option B — HTML 문자열 리턴

**흐름**
```
앱 → GET /api/v1/reports/{id}?format=html
   → {"html": "<html>...</html>"} 리턴
   → 앱 WebView.loadData(html)
```

**장점**
- 수신 후 오프라인 캐싱 가능
- 앱 내부 저장 후 재열람 용이

**단점**
- 응답 페이로드 큼 (HTML 전체)
- 앱이 캐싱 로직 직접 구현해야 함

**앱팀 작업량**  
WebView.loadData() + 캐싱 처리

---

### Option C — 네이티브 렌더링 (현재 방식 유지)

**흐름**
```
앱 → GET /api/v1/reports/{id} → JSON 리턴
   → 앱이 네이티브 UI로 직접 렌더링
```

**장점**
- 가장 앱다운 UX, 성능 최고
- 앱 디자인 자유도 높음

**단점**
- 앱 개발 공수 가장 큼
- AI 코멘트·수면 가이드 등 텍스트 레이아웃 앱팀이 직접 구현
- 디자인 변경 시 앱 업데이트 필요

**앱팀 작업량**  
리포트 전체 UI 신규 개발

---

### Option D — PDF API

**흐름**
```
앱 → GET /api/v1/reports/{id}/pdf → PDF 파일 다운로드
```

**장점**
- 저장·공유·인쇄에 최적
- 병원 상담 시 지참 가능

**단점**
- 서버 PDF 생성 부하 (Puppeteer 또는 WeasyPrint 필요)
- 동적 인터랙션 불가

**앱팀 작업량**  
파일 다운로드·저장 처리

---

## 협의 포인트

| 항목 | 질문 |
|------|------|
| 표시 방식 | 리포트를 앱 내 WebView로 표시할지, 네이티브 UI로 구현할지 |
| 재열람 | 오프라인에서도 이전 리포트를 볼 수 있어야 하는지 |
| PDF | PDF 저장·공유 기능이 필요한지 |
| 디자인 주도 | 리포트 디자인을 서버팀이 관리할지, 앱팀이 가져갈지 |
| 인증 | 앱에서 WebView 호출 시 JWT 토큰 전달 방식 (헤더 vs 쿼리파라미터) |

---

## 서버팀 현황

- 현재 HTML 리포트 렌더링 코드 완성 (Chart.js 레이더·막대 차트 포함)
- Option A 선택 시 Jinja2 템플릿 이식 작업 약 1~2일 예상
- Option D 선택 시 Puppeteer 또는 WeasyPrint 도입 필요 (추가 검토 필요)
- JSON API(현재)는 Option C, D 모두 그대로 활용 가능
