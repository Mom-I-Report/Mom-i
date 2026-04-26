# 도메인 지식 → 코드 적용 분석

날짜: 2026-04-26  
브랜치: feat/noh  
분석 대상: `prompts/knowledge.md`, `report_service.py`, `gemini_client.py`

---

## 개요

`knowledge.md`에 정의된 도메인 지식이 백엔드 코드에 어떻게 반영되는지 매핑.  
크게 두 가지 경로로 나뉜다:
1. **코드 직접 계산**: Python에서 판정 후 레이블/불리언으로 Gemini에 전달
2. **Gemini 위임**: raw 수치를 그대로 전달하고 Gemini가 프롬프트 기준으로 판단

---

## 도메인 지식별 코드 반영 현황

### 1. AAP 권장 수면 시간

| 월령 | knowledge.md | report_service.py (`_build_pattern_summary`) |
|------|-------------|----------------------------------------------|
| 0~3개월 | 14~17시간 | `recommended = (14, 17)` |
| 4~11개월 | 12~15시간 | `recommended = (12, 15)` |
| 12~23개월 | 11~14시간 | `recommended = (11, 14)` |
| 24개월 이상 | 10~13시간 | `recommended = (10, 13)` |

**판정 방식**: `avg_sleep_h < recommended[0] - 1` → 수면 부족 / `> recommended[1]` → 수면 충분 / 그 외 → 정상 범위  
**전달 방식**: `pattern_summary` 필드에 "수면 부족" / "수면 정상 범위" / "수면 충분" 텍스트로 전달 → Gemini `ai_comment` 작성 시 활용  
**판정 주체**: ✅ 코드 직접 계산

---

### 2. AAP 정상 호흡수 범위 (수면 중)

| 월령 | knowledge.md | `_BREATH_RANGES` |
|------|-------------|------------------|
| 0~3개월 | 30~55회/분 | `(3, 30, 55)` |
| 3~6개월 | 25~50회/분 | `(6, 25, 50)` |
| 6~12개월 | 20~40회/분 | `(12, 20, 40)` |
| 12~24개월 | 20~35회/분 | `(24, 20, 35)` |
| 24개월 이상 | 20~30회/분 | `(999, 20, 30)` |

**판정 방식**: `b_min <= breath_avg <= b_max` → `is_normal` 불리언  
**전달 방식**: `breath_is_normal`, `breath_normal_range` (예: "20~40회/분 (생후 12개월 이하 기준)") Gemini에 전달  
**판정 주체**: ✅ 코드 직접 계산

---

### 3. 체온 기준

| 기준 | knowledge.md | `_BODY_TEMP_*` 상수 |
|------|-------------|---------------------|
| 정상 | 37.4°C 이하 | `_BODY_TEMP_NORMAL_MAX = 37.4` |
| 미열 주의 | 37.5~37.9°C | `_BODY_TEMP_CAUTION_MAX = 37.9` |
| 발열 의심 | 38.0°C 이상 | 38.0 이상 = 발열 의심 |

**판정 방식**: `_get_body_temp_status(body_temp_max)` → "정상" / "미열 주의" / "발열 의심" 문자열  
**전달 방식**: `body_temp_status` 필드로 Gemini에 전달. `temp_extra` 문자열로 소아과 상담 권장 여부도 포함  
**판정 주체**: ✅ 코드 직접 계산

---

### 4. 뒤척임 해석 기준

| 기준 | knowledge.md | `_build_pattern_summary` |
|------|-------------|--------------------------|
| 적음 | ≤ 20분 | `avg_restless_min <= 20` → "뒤척임 적음" |
| 보통 | 21~40분 | `avg_restless_min <= 40` → "뒤척임 보통" |
| 과다 | > 40분 | 그 외 → "뒤척임 과다" |

**전달 방식**: `pattern_summary`에 포함  
**판정 주체**: ✅ 코드 직접 계산

---

### 5. 실내 환경 기준 (온도 / 소음)

| 항목 | knowledge.md | 코드 처리 |
|------|-------------|-----------|
| 적정 온도 | 20~22°C | 판정 없음, raw 수치 전달 |
| 소음 (조용) | < 45dB | 판정 없음, raw 수치 전달 |
| 소음 (보통) | 45~60dB | 판정 없음, raw 수치 전달 |
| 소음 (시끄러움) | > 60dB | 판정 없음, raw 수치 전달 |

**전달 방식**: `temp_avg`, `temp_max`, `temp_min`, `db_avg`, `db_max` raw 수치 그대로 Gemini에 전달  
**판정 주체**: ⚙️ Gemini 위임 (knowledge.md 참고해서 직접 판단)  
**이유**: 환경 판단은 복합 요소(온도×소음 조합, 계절 등)가 있어 Gemini 판단이 더 적합

---

### 6. 수면 교육법 선택

7가지 수면 교육법(퍼버, 의자, 쉬닥, 안눈법, 픽업앤다운, EASY, 자장가)은 knowledge.md에 정의.

**판정 주체**: ⚙️ Gemini 위임  
- `age_policy.md`로 월령별 허용/금지 제한  
- `reasoning.md`로 데이터 기반 선택 강제  
- 코드에서는 `baby_age_months`만 전달

---

### 7. 원더윅스 판정

`output_format.md`에 공식 정의: `baby_age_months × 4.3 ≈ 주령, ±1주 이내이면 is_wonder_weeks: true`

**판정 주체**: ⚙️ Gemini 위임  
- 코드에서는 `baby_age_months`만 전달  
- Gemini가 공식으로 직접 판단 후 `age_kick.is_wonder_weeks` 필드 반환

---

## 데이터 흐름 전체 도식

```
요청 수신 (GenerateReportRequest)
        │
        ▼
코드 직접 계산 (report_service.py)
  ├─ _build_summary()        → 평균 수면, 뒤척임, 이벤트
  ├─ _build_breath_summary() → is_normal (AAP 기준 판정)
  ├─ _build_body_temp_summary() → status (정상/미열/발열)
  └─ _build_pattern_summary() → "수면 정상 범위 / 뒤척임 보통" 한 줄 요약
        │
        ▼
컨텍스트 구성 (_build_ai_context)
  ├─ baby_age_months (원더윅스·age_policy 판단용)
  ├─ pattern_summary (코드 판정 결과 요약)
  ├─ this_week (수면+환경 raw + 호흡/체온 판정 포함)
  ├─ daily (7일치)
  ├─ last_week (있을 경우)
  └─ two_weeks_ago (있을 경우)
        │
        ▼
Gemini 위임 (gemini_client.py)
  system_instruction = system.md + knowledge.md + age_policy.md
                       + reasoning.md + output_format.md
  user_prompt = input_template.md + 상세 데이터 블록
        │
        ▼
JSON 반환 + 필드 검증
  ai_comment / sleep_guide / age_kick
```

---

## 발견된 버그 및 수정 사항

### 버그: sleep_guide / age_kick null 처리 오류

**위치**: `report_service.py:455-456`

**문제**: 0~2개월 아기일 때 Gemini가 `sleep_guide: null` 반환.  
`"sleep_guide" in ai_result` → True이지만 `SleepGuide(**None)` → `TypeError`

**수정 전**:
```python
sleep_guide = SleepGuide(**ai_result["sleep_guide"]) if "sleep_guide" in ai_result else None
age_kick    = AgeKick(**ai_result["age_kick"]) if "age_kick" in ai_result else None
```

**수정 후**:
```python
sleep_guide = SleepGuide(**ai_result["sleep_guide"]) if ai_result.get("sleep_guide") else None
age_kick    = AgeKick(**ai_result["age_kick"]) if ai_result.get("age_kick") else None
```

`ai_result.get("sleep_guide")`는 `None`이면 falsy → 안전하게 `None` 반환.

---

## 총평

| 항목 | 상태 |
|------|------|
| AAP 수면 시간 기준 | ✅ 코드 직접 반영 |
| AAP 호흡수 기준 | ✅ 코드 직접 반영 |
| 체온 기준 | ✅ 코드 직접 반영 |
| 뒤척임 해석 | ✅ 코드 직접 반영 |
| 실내 환경 기준 | ⚙️ Gemini 위임 (의도적) |
| 수면 교육법 선택 | ⚙️ Gemini 위임 (의도적) |
| 원더윅스 판정 | ⚙️ Gemini 위임 (의도적) |
| sleep_guide null 처리 | ✅ 버그 수정 완료 |

**결론**: 도메인 지식이 코드와 프롬프트에 올바르게 분리·적용됨.  
수치 판정(AAP 기준)은 코드에서 미리 처리해 Gemini 부담을 줄이고, 해석·추천 판단은 Gemini에 위임하는 설계가 유지됨.
