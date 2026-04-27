# Mom-i 리포트 서버 — 시스템 플로우

> 코드 기준: 2026-04-27 / `feat/noh` 브랜치

---

## 전체 구조

```
EMTAKE 카메라
    │
    ▼
맘아이 메인 서버 ──POST /api/v1/reports/generate──► 리포트 서버 ──► Gemini API
맘아이 앱        ──GET  /api/v1/reports           ──► 리포트 서버 ──► DB
관리자           ──GET  /api/v1/admin/...         ──► 리포트 서버 ──► DB
```

---

## 1. 리포트 생성 플로우

```
맘아이 서버
  │  POST /api/v1/reports/generate
  │  Header: X-API-Key
  │  Body: { ser_no, week_start, baby_age_months, weekly_data }
  ▼
[security] verify_api_key()
  ▼
[report_service] generate_report()
  │
  ├─ 1. Weekly_Data UPSERT  ← 항상 최신 데이터로 갱신
  │
  ├─ 2. Generated_Reports 캐시 확인
  │       ├─ HIT  → Gemini 호출 없이 즉시 반환
  │       └─ MISS → 계속
  │
  ├─ 3. 이전 2주치 Weekly_Data 조회  ← trend + AI 컨텍스트 공용
  │
  ├─ 4. 집계
  │       ├─ summary  (avg_sleep_h, avg_restless_min, cry_count)
  │       ├─ daily    (요일별 sleep_h, restless_min)
  │       ├─ breath   (breath_avg, is_normal)
  │       ├─ body_temp(body_temp_avg, status)
  │       └─ trend    (전주 대비 수면/뒤척임/울음 차이)
  │
  ├─ 5. gemini_client.generate_insight()
  │       ├─ 최대 3회 재시도
  │       ├─ response_mime_type: "application/json" 강제
  │       └─ _validate_json() → 필드 누락 시 보정 프롬프트 재호출
  │
  ├─ 6. Generated_Reports UPSERT
  │
  └─ 7. 응답 반환
         { ser_no, week_start, week_label,
           summary, breath, body_temp, daily, trend,
           ai_comment, sleep_guide, age_kick }
```

---

## 2. 앱 리포트 조회 플로우

```
맘아이 앱
  │  GET /api/v1/reports
  │  Header: Authorization: Bearer <JWT>
  ▼
[security] get_current_ser_no()  ← JWT payload.ser_no 추출
  ▼
[report_repo] get_reports_by_ser_no(ser_no, limit=10)
  ▼
응답: 최근 10건 리포트 목록 (report_id, week_start, week_label, report_json)
```

```
맘아이 앱
  │  GET /api/v1/reports/{report_id}
  ▼
[security] get_current_ser_no()  ← ser_no 검증 (타인 리포트 접근 차단)
  ▼
[report_repo] get_report_by_id(report_id, ser_no)
  ▼
응답: 리포트 전체 JSON
```

---

## 3. 관리자 플로우

```
관리자
  │  Header: X-API-Key
  ▼
GET /api/v1/admin/stats
  └─ 전체 통계 (총 기기 수, 리포트 수, 최근 생성 시각)

GET /api/v1/admin/devices
  └─ 기기 목록 (ser_no, subscribed_at, last_report_at, report_count)

GET /api/v1/admin/devices/{ser_no}/reports
  └─ 해당 기기 최근 3주치 리포트 (report_id, week_start, report_json)
```

---

## 4. 스케줄러 (Rolling 삭제)

```
APScheduler — 매주 월요일 10:00 KST
  ▼
[report_repo] delete_old_data()
  ├─ Weekly_Data    → 12주 이전 데이터 물리 삭제
  └─ Generated_Reports → 5주 이전 데이터 물리 삭제
```

---

## 5. Gemini 출력 → report_json 변환

```
Gemini 출력 (JSON)          report_json 최종 필드
─────────────────────────   ──────────────────────────────
ai_comment[ ]            →  ai_comment
sleep_guide{ }           →  sleep_guide  (+ kick_action optional)
age_kick{ }              →  age_kick

+ 코드 집계:
  summary                →  summary
  daily                  →  daily
  breath                 →  breath
  body_temp              →  body_temp
  trend                  →  trend
```

---

## 6. 인증 구조

| 엔드포인트 | 인증 방식 | 검증 내용 |
|-----------|-----------|---------|
| `POST /api/v1/reports/generate` | X-API-Key | 환경변수 API_KEY 일치 |
| `GET /api/v1/reports` | JWT Bearer | HS256 서명, payload.ser_no 추출 |
| `GET /api/v1/reports/{id}` | JWT Bearer | ser_no 격리 (타인 접근 차단) |
| `GET /api/v1/admin/*` | X-API-Key | 환경변수 API_KEY 일치 |
