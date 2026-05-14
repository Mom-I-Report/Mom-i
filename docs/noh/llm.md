# LLM(Gemini) 사용 구조

## 개요

이 서버는 **Gemini 3.1 Flash-Lite** 모델을 사용해 영유아 주간 수면 데이터를 분석하고, 부모에게 AI 코멘트·수면 가이드·발달 정보를 제공하는 리포트를 생성한다.

```
맘아이 서버 ──POST /generate──► report_service.py ──► gemini_client.py ──► Gemini API
                                      │                        │
                               데이터 집계/전처리          프롬프트 조립 & 호출
```

---

## 1. 모델 정보

| 항목 | 값 |
|------|---|
| 모델 | `gemini-3.1-flash-lite` |
| 출력 형식 | `application/json` (response_mime_type으로 강제) |
| Thinking | `thinking_level="minimal"` |
| 최대 재시도 | 5회 |
| 백오프 | 지수 (5s → 10s → 20s → 40s → 80s) |
| 재시도 대상 오류 | 429 (Rate Limit), 503 (Unavailable) |

---

## 2. 시스템 프롬프트 구조

`gemini_client.py`는 모듈 로드 시 5개 프롬프트 파일을 `---` 구분자로 이어붙여 단일 `system_instruction`으로 조립한다.

```
backend/app/infrastructure/llm/prompts/
├── system.md          # 역할 정의, HARD RULES, 톤/스타일
├── knowledge.md       # 판단 기준 (수면·호흡·체온·환경·수면법 정의)
├── age_policy.md      # 월령별 수면법 허용/금지 목록
├── reasoning.md       # 추론 규칙 (데이터 기반 판단, 금지 표현 등)
└── output_format.md   # JSON 출력 스키마 + 작성 규칙
```

### 조립 순서

```python
_SYSTEM_PROMPT = (
    system.md + "---" + knowledge.md + "---" + age_policy.md + "---" + reasoning.md
    + "---"
    + output_format.md   # 출력 형식은 마지막에 배치
)
```

### 각 파일 역할 요약

**`system.md` — 역할 & 규칙**
- 역할: "영유아 수면 데이터 기반 가이드 리포트 생성기"
- HARD RULES 7가지 (진단 금지, 부모 불안 유발 금지, 킥 액션 필수 등)
- 톤: 차분한 육아 코치, 명령 아닌 제안

**`knowledge.md` — 판단 기준 DB**
- 월령별 권장 수면 시간 (AAP 기준)
- 낮잠 전환 시기, 수면 퇴행, 분리불안 시기
- 취침 권장 시간대 (월령별)
- 정상 호흡수 범위 (월령별, 수면 중)
- 체온 판정 기준 (EMTAKE 델타값 기준)
- 뒤척임 해석 기준, 실내 환경 기준 (온도·소음·습도·조도)
- 수면 교육법 7종 정의 (퍼버법·쉬닥법·안눈법 등)
- 원더윅스 기준 주령 목록

**`age_policy.md` — 월령별 수면법 제한**
- 0~2개월: 수면 교육 전체 금지 (`sleep_guide: null`)
- 3~4개월: 쉬닥법·안눈법만 허용 (퍼버법 금지)
- 5~6개월: 쉬닥법·퍼버법(초기)·픽업앤다운
- 7~9개월: 퍼버법·쉬닥법·픽업앤다운
- 10~12개월: 퍼버법 중심 + 루틴 강화
- 13개월 이상: 퍼버법·의자법 + 루틴 일관성

**`reasoning.md` — 추론 규칙**
- "가능성"만 표현, 확정 금지
- 데이터와 연결되지 않은 해석 금지
- AGE POLICY 우선 적용 (금지 수면법 절대 언급 금지)
- sleep_guide는 단일 방법만 선택

**`output_format.md` — JSON 스키마**
- 출력할 JSON 구조 명세 (아래 섹션 참고)
- 작성 규칙: 아기 호칭 통일, 수치 해석 제공, 의학 진단 표현 금지 등

---

## 3. 입력 데이터 (User Prompt)

`_build_prompt(ctx: dict)` 함수가 `input_template.md` + 상세 데이터 블록을 조합해 user prompt를 만든다.

### 템플릿 변수 치환 (`input_template.md`)

```
아기 월령: {{age_month}}           → "8개월 (약 34주령)"
이번 주 평균 수면: {{avg_sleep}}   → "11.5시간"
울음 감지 횟수: {{wake_count}}     → "3회"
수면 환경 온도: {{temperature}}    → "평균 21.5°C"
패턴 요약: {{pattern_summary}}     → "수면 부족 / 뒤척임 과다 / 미열 주의"
```

`pattern_summary`는 `_build_pattern_summary()`가 수면·호흡·체온 상태를 `/`로 이어붙인 한 줄 문자열로 생성한다 (AI의 빠른 상황 파악용).

### 상세 데이터 블록 (하드코딩 포맷)

```
[상세 데이터]
주간: 뒤척임 35분 / 월간 평균 수면 11.8h / 주간 평균 수면 11.5h
환경: 온도 21.5°C (최고 24 / 최저 19) ✅ 권장 범위 (18~22°C) 내 / 소음 최고 58dB
호흡: 평균 28회/분 (최소 20 / 최대 36) — 정상 범위 내 (20~40회/분 ...)
체온: 평균 0.3°C / 최고 0.7°C — 정상

[일별 수면] (평균 취침 21:00 — 권장보다 30분 늦음 ⚠)
  월: 수면 11.2h / 뒤척임 40분 / 총뒤척임 3회 / 낮잠 2회 / 밤잠 21:00~06:00(540분)
  화: ...

[지난 주 대비]    ← prev_data[0] 있을 때
수면: 10.5h → 11.5h / 뒤척임: 45분 → 35분
...

[2주 전]          ← prev_data[1] 있을 때
수면 10.0h / 뒤척임 50분 / ...
```

### 컨텍스트 소스별 활용

| 소스 | 활용 목적 |
|------|---------|
| 이번 주 (`this_week`) | 현재 상태 판단, 수면법 추천 근거 |
| 직전 주 (`last_week`) | 변화 방향 언급 (ai_comment 트렌드) |
| 2주 전 (`two_weeks_ago`) | 장기 트렌드 판단 |

---

## 4. 출력 JSON 구조

```json
{
  "ai_comment": [
    {
      "type": "caution",        // "caution" | "good"
      "icon": "🌡️",
      "title": "주의 항목 (15자 이내)",
      "text": "데이터 기반 설명 (2~3문장)"
    },
    {
      "type": "good",
      "icon": "😴",
      "title": "긍정 항목 (15자 이내)",
      "text": "데이터 기반 긍정 관찰 (2~3문장)"
    }
    // 총 2~3개, 최소 caution 1개 + good 1개
  ],
  "sleep_guide": {              // 0~2개월이면 null
    "method_name": "퍼버법",
    "title": "✨ '퍼버법'으로 시도해볼 수 있는 수면 가이드",
    "reason": "이 방법 선택 근거 (이번 주 데이터 포함, 2~3문장)",
    "steps": [
      "1단계: ...",
      "2단계: ...",
      "3단계: ..."
    ],
    "kick_action": "오늘 밤 바로 ___ 해보세요 (구체적 행동 1가지)"
  },
  "age_kick": {
    "title": "이번 월령 발달 이슈 제목",
    "text": "이슈 설명 및 부모 대처 팁 (3~4문장)",
    "is_wonder_weeks": false    // 원더윅스 기준 주령 ±1주 이내이면 true
  },
  "parent_message": "보호자 응원 메시지 (1~2문장, 이모지 1개 포함)"
}
```

---

## 5. 전체 호출 흐름

### `report_service.generate_report()` → `gemini_client.generate_insight()`

```
generate_report()
  │
  ├── Step 1: Weekly_Data upsert (항상 실행)
  ├── Step 2: Generated_Reports 캐시 확인 → 있으면 Gemini 호출 생략
  ├── Step 3: get_recent_weekly_data(weeks=2) — 이전 2주치 1회 조회
  ├── Step 4: 데이터 집계
  │     ├── _build_summary()           : 주간 평균 수면·뒤척임·이벤트·환경
  │     ├── _build_daily()             : 7일치 일별 DailySummary
  │     ├── _build_breath_summary()    : 호흡수 + AAP 기준 정상 여부
  │     ├── _build_body_temp_summary() : 체온 + 상태 판정
  │     └── _build_trend()             : 직전 주 대비 변화량 5개 지표
  │
  └── Step 5: AI 조언 생성
        ├── _build_ai_context()        : 최대 3주치 컨텍스트 dict 조립
        └── await generate_insight(ctx)
              │
              ├── _build_prompt(ctx)   : user prompt 문자열 생성
              ├── _call_gemini(prompt) : Gemini 비동기 호출 (재시도 포함)
              ├── json.loads(raw)      : JSON 파싱
              └── _validate_json(data) : 필드 검증 → 누락 시 보정 재호출
```

### `_call_gemini()` 내부 재시도 로직

```
시도 1 실패 (429/503) → 5초 대기 → 시도 2
시도 2 실패 (429/503) → 10초 대기 → 시도 3
시도 3 실패 (429/503) → 20초 대기 → 시도 4
시도 4 실패 (429/503) → 40초 대기 → 시도 5
시도 5 실패 → 예외 raise
```

---

## 6. JSON 검증 및 보정 재호출

`_validate_json(data)`가 응답 구조를 검사한다.

**필수 최상위 필드:**
- `ai_comment` (list 타입)
- `sleep_guide` (dict, 하위 필드: `method_name`, `title`, `reason`, `steps`, `kick_action`)
- `age_kick` (dict, 하위 필드: `title`, `text`, `is_wonder_weeks`)
- `parent_message` (str 타입)

**보정 흐름:**

```
1차 호출 → JSON 파싱 실패 → "유효한 JSON만 출력" 지시 후 재호출
1차 호출 → 파싱 성공 → 필드 누락 발견 → 누락 필드 명시 후 재호출
재호출 후에도 누락 → 에러 로깅 후 현재 결과 반환 (서비스 중단 방지)
```

---

## 7. 토큰 로깅

매 Gemini 호출마다 `usage_metadata`에서 토큰 수를 읽어 INFO 레벨로 기록한다.

```
[Gemini 토큰] 입력: 1842 / 출력: 523 / 합계: 2365
```

비용 추적 및 프롬프트 최적화에 활용.

---

## 8. 캐싱 전략

동일 `(ser_no, week_start)` 조합으로 이미 생성된 리포트가 있으면 Gemini를 재호출하지 않는다.

- `Weekly_Data`는 **항상 upsert** (캐시 히트여도 실행) — 다음 주 AI 트렌드 컨텍스트를 최신으로 유지하기 위함
- `Generated_Reports`가 캐시 역할 — 주차별 1건만 보존

---

## 9. 사전 집계 로직 (백엔드, LLM 호출 전)

LLM에 넘기기 전 백엔드가 직접 처리하는 판정들:

| 판정 항목 | 기준 | 파일 |
|----------|------|------|
| 호흡 정상 여부 | AAP 월령별 범위 (평균 기준) | `report_service.py:_build_breath_summary` |
| 체온 상태 | 델타 0.9/1.4°C 기준 | `report_service.py:_get_body_temp_status` |
| 실내 온도 경고 | 신생아 20~22°C / 일반 18~22°C | `gemini_client.py:_build_prompt` |
| 취침 시간 판정 | 월령별 권장 범위 대비 평균 취침 시간 | `gemini_client.py:_build_prompt` |
| 습도·조도 경고 | 40~60% / 5lux 이하 | `gemini_client.py:_build_prompt` |
| 패턴 요약 | 수면량·뒤척임·호흡·체온을 한 줄 텍스트로 | `report_service.py:_build_pattern_summary` |

이 사전 판정 결과가 프롬프트에 포함되어 LLM이 올바른 판단을 내리도록 유도한다.
