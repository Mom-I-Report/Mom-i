# E2E 테스트 — 백엔드 리포트 생성 검증

**작성일**: 2026-06-02  
**테스트 환경**: Docker (MariaDB 10.11 + FastAPI 앱 컨테이너)  
**테스트 목적**: 리포트 생성 API 전체 흐름, 계산 정확성, env 이상 감지 동작 확인

---

## 환경 준비

```bash
# Docker Desktop 실행 후
cd Mom-i
docker-compose up -d

# 헬스체크
curl http://localhost:8000/health
# → {"status":"ok","version":"0.2.0"}
```

DB 테이블 확인:
```bash
docker exec momi_db mariadb -u momi_user -p1234 momi_db -e "SHOW TABLES;"
# → Generated_Reports / Share_Targets / Weekly_Data
```

---

## 테스트 1 — 리포트 생성 (신규 ser_no)

> 캐시 히트를 피하려면 DB에 없는 `ser_no` 사용할 것.  
> 기존 `MT-00001`은 이전 세션 캐시 데이터가 있어 재계산 안 함.

### 요청

```bash
curl -s -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-local-key" \
  -d '{
  "ser_no": "MT-E2E-TEST",
  "baby_age_months": 8,
  "week_start": "2026-05-25",
  "sleep": [
    {"date":"2026-05-25","sleep_min":620,"restless_min":25,"wakeup_count":2,"device_status":"NORMAL","env_temp_max":22.1,"env_db_max":48,"env_humidity_avg":52.0,"env_bright_avg":1.2},
    {"date":"2026-05-26","sleep_min":580,"restless_min":30,"wakeup_count":3,"device_status":"NORMAL","env_temp_max":22.8,"env_db_max":51,"env_humidity_avg":53.0,"env_bright_avg":1.5},
    {"date":"2026-05-27","sleep_min":510,"restless_min":52,"wakeup_count":5,"device_status":"CAUTION","env_temp_max":25.3,"env_db_max":49,"env_humidity_avg":54.0,"env_bright_avg":1.8},
    {"date":"2026-05-28","sleep_min":600,"restless_min":20,"wakeup_count":2,"device_status":"NORMAL","env_temp_max":21.9,"env_db_max":47,"env_humidity_avg":51.0,"env_bright_avg":1.3},
    {"date":"2026-05-29","sleep_min":590,"restless_min":35,"wakeup_count":3,"device_status":"NORMAL","env_temp_max":22.5,"env_db_max":50,"env_humidity_avg":52.5,"env_bright_avg":1.4},
    {"date":"2026-05-30","sleep_min":540,"restless_min":42,"wakeup_count":4,"device_status":"NORMAL","env_temp_max":23.8,"env_db_max":55,"env_humidity_avg":50.0,"env_bright_avg":1.6},
    {"date":"2026-05-31","sleep_min":610,"restless_min":22,"wakeup_count":2,"device_status":"NORMAL","env_temp_max":22.2,"env_db_max":48,"env_humidity_avg":53.0,"env_bright_avg":1.2}
  ],
  "environment": {"temp_avg":23.2,"temp_max":24.5,"temp_min":21.8,"db_max":52,"db_avg":52,"humidity_min":45,"humidity_max":58,"humidity_avg":51.5,"bright_min":0.2,"bright_max":3.5,"bright_avg":1.85},
  "breath": {"breath_min":32,"breath_max":52,"breath_avg":40},
  "body_temp": {"body_temp_min":-0.3,"body_temp_max":0.6,"body_temp_avg":0.2},
  "monthly": {"month_sleep_h":14.5,"month_restless_h":0.55,"week_sleep_h":13.8,"week_restless_h":0.5},
  "events": {"cry_count":4,"leave_count":1}
}'
```

**테스트 데이터 설계 포인트**:
- `baby_age_months: 8` → 8개월 아기 기준 (권장 수면 12~15h)
- 수요일(2026-05-27) `env_temp_max: 25.3` → 권장 범위(20~22°C) 초과, AI 경고 트리거용
- 수요일 `device_status: CAUTION`, `restless_min: 52` → 패턴 이상 강조
- `week_start: 2026-05-25` (월요일) → 7일 날짜 연속성 확인

### 기대 결과 및 실제 결과

| 항목 | 계산 근거 | 기대값 | 실제값 | 결과 |
|------|-----------|--------|--------|------|
| `summary.avg_sleep_h` | (620+580+510+600+590+540+610)/7/60 | 9.6 | **9.6** | ✅ |
| `summary.avg_restless_min` | (25+30+52+20+35+42+22)/7 | 32 | **32** | ✅ |
| `summary.humidity_avg` | 요청값 그대로 | 51.5 | **51.5** | ✅ |
| `daily[수]` sleep_h | 510/60 | 8.5h | **8.5h** | ✅ |
| `breath.is_normal` | avg=40, 8개월 정상범위 20~40 | true | **true** | ✅ |
| `body_temp.status` | max=0.6 < 0.9 | 정상 | **정상** | ✅ |
| `trend` | 첫 주차, 이전 데이터 없음 | null | **null** | ✅ |
| `ai_comment` caution | 수요일 25.3°C 감지 | 온도 경고 | **🌡️ 실내 환경 온도 점검** | ✅ |
| `sleep_guide` | 있음 | method_name | **쉬닥법** | ✅ |
| `age_kick` | 있음 | title | **분리불안과 도약기** | ✅ |

---

## 테스트 2 — 캐시 동작 확인

같은 `ser_no` + `week_start`로 재호출하면 Gemini 재호출 없이 캐시 반환.

```bash
# 두 번째 호출 — 응답값 동일, 백엔드 로그에 "캐시 히트" 출력
docker logs momi_app --tail=5
# → [INFO] ... [리포트 캐시 히트] ser_no=MT-E2E-TEST week_start=2026-05-25 — Gemini 재호출 생략
```

---

## 테스트 3 — 공유 목록 API 인증 확인

```bash
# 인증 없이 호출 → 401
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/share-targets
# → 401

# 등록 엔드포인트 확인 (openapi)
curl -s http://localhost:8000/openapi.json | grep -o '"\/api\/v1\/share[^"]*"'
# → "/api/v1/share-targets"
# → "/api/v1/share-targets/{target_id}"
```

---

## 주의사항

- **캐시 주의**: 같은 `ser_no` + `week_start` 조합이 DB에 이미 있으면 캐시 응답 반환. 새로 테스트할 때는 `ser_no`를 바꾸거나 DB에서 해당 행 삭제.
- **JWT 없음**: 현재 테스트는 `X-API-Key`(서버 to 서버) 방식만 검증. 앱 JWT 엔드포인트(`GET /api/v1/reports`)는 맘아이 서버에서 발급한 JWT 필요.
- **Gemini 소요시간**: 리포트 최초 생성 시 10~20초 소요. 타임아웃 설정 주의.

---

## DB 직접 확인

```bash
# 최근 생성된 리포트 목록
docker exec momi_db mariadb -u momi_user -p1234 momi_db \
  -e "SELECT ser_no, week_start, JSON_EXTRACT(report_json, '$.summary.avg_sleep_h') as avg_sleep_h FROM Generated_Reports ORDER BY created_at DESC LIMIT 5;"

# Share_Targets 확인
docker exec momi_db mariadb -u momi_user -p1234 momi_db \
  -e "SELECT * FROM Share_Targets;"
```
