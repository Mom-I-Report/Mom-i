# 프롬프트 컨텍스트 엔지니어링 작업 정리

> 작업일: 2026-04-26  
> 작업자: noh  
> 브랜치: feat/noh

---

## 1. 작업 배경

`backend/app/prompt/` 폴더에 새 프롬프트 파일 6개가 추가되어 있었으나, 실제 Gemini 호출에는 전혀 반영되지 않은 상태였다.  
기존에는 `infrastructure/llm/prompts/system_prompt.md` 단일 파일만 system instruction으로 사용 중이었다.

이번 작업의 목표:
- 새 프롬프트 파일들의 내용을 실제 AI 호출에 반영
- 단일 파일 구조 → 역할별로 분리된 모듈 구조로 개선
- 파일 위치를 LLM 인프라(`infrastructure/llm/prompts/`) 아래로 통합

---

## 2. 변경 전/후 구조

### 변경 전

```
backend/app/
  prompt/                          ← 사용 안 됨 (dead code)
    1_SYSTEM.md.txt
    2_KNOWLEDGE BLOCK.md.txt
    3_AGE POLICY.md.txt
    4_INPUT.md.txt
    5_REASONING CONSTRAINT.md.txt
    6_OUTPUT FORMAT.md.txt
  infrastructure/
    llm/
      gemini_client.py
      prompts/
        system_prompt.md           ← 유일하게 사용되던 파일
```

### 변경 후

```
backend/app/infrastructure/llm/
  gemini_client.py
  prompts/
    system.md           ← 역할, HARD RULES, STYLE
    knowledge.md        ← 판단 기준 전체 (수면/호흡/체온/수면법/원더윅스)
    age_policy.md       ← 월령별 수면법 제한
    reasoning.md        ← 추론 규칙
    input_template.md   ← user prompt 템플릿 (변수 치환)
    output_format.md    ← JSON 출력 형식 + 최종 규칙
```

---

## 3. 프롬프트 파일별 역할

### system.md — 역할 · HARD RULES · STYLE

AI의 정체성과 절대 지켜야 할 행동 원칙을 정의한다.

**변경 포인트:**
- 역할 명칭 변경: `"영유아 수면 전문 분석가"` → `"영유아 수면 데이터 기반 가이드 리포트 생성기"`
- 목표 명시 추가: *"부모가 오늘 바로 실행할 수 있는 행동을 제시하는 것"*
- **HARD RULES 7개 신규 추가** (원래 없었음):
  1. 제공된 데이터 외 추측 금지
  2. 효과 단정 표현 금지 ("개선됩니다" ❌)
  3. 수면법은 '추천'이 아닌 '가능한 선택지'로 제시
  4. 아기 상태를 문제로 규정하지 말 것
  5. 부모를 비난하거나 불안 유발 금지
  6. 반드시 현실적인 행동 가이드 포함
  7. 핵심 행동(킥) 반드시 포함
- **STYLE 신규 추가** (원래 없었음): 차분한 톤, 육아 코치 느낌, 명령 X 제안 O

---

### knowledge.md — 판단 기준 (도메인 지식)

Gemini가 데이터를 해석할 때 사용하는 기준값 전체.

**변경 포인트:**
- 기존 내용 유지: AAP 수면 시간 기준, 호흡수 기준, 체온 판정, 뒤척임 해석, 실내 환경 기준, 원더윅스
- **수면 교육법 2개 추가** (기존 5개 → 7개):

| 추가된 교육법 | 특징 |
|-------------|------|
| 안눈법 (No Tears) | 울음 최소화, 즉각 반응, 민감한 아기에 적합 |
| 픽업앤다운 | 울면 안고 진정 후 내려놓기 반복, 중간 단계 전환기 |

전체 수면 교육법 목록: 퍼버법, 의자법, 쉬닥법, 안눈법, 픽업앤다운, EASY 루틴, 자장가 루틴

---

### age_policy.md — 월령별 수면법 제한 (신규)

원래 없던 파일. 월령에 따라 사용 금지 수면법을 명시한다.  
이 정책 없이는 Gemini가 0개월 아기에게 퍼버법을 추천하는 등 부적절한 응답을 낼 수 있었다.

| 월령 | 허용 | 금지 |
|------|------|------|
| 0~2개월 | 환경 조성만 (`sleep_guide: null`) | 수면 교육 전체 금지 |
| 3~4개월 | 쉬닥법, 안눈법 | 퍼버법 |
| 5~6개월 | 쉬닥법, 퍼버법(초기), 픽업앤다운 | — |
| 7~9개월 | 퍼버법, 쉬닥법, 픽업앤다운 | — |
| 10~12개월 | 퍼버법 중심 + 루틴 강화 | — |
| 13개월 이상 | 퍼버법, 의자법 + 루틴 일관성 유지 | — |

---

### reasoning.md — 추론 규칙 (신규)

원래 없던 파일. Gemini가 결론을 도출하는 방식에 대한 제약.

- "가능성"만 말하고 확정 금지
- 데이터와 연결되지 않은 해석 금지
- 월령 정책(age_policy.md) 반드시 준수
- 수면법 선택 이유를 반드시 데이터 기반으로 설명
- sleep_guide에는 1개 방법만 선택, 나머지는 대안 제시

---

### input_template.md — User Prompt 템플릿

Gemini에 전달하는 user prompt의 기본 입력 구조.  
`_build_prompt()`에서 `{{변수}}` 치환 후 상세 데이터 블록을 append한다.

| 변수 | 매핑 | 비고 |
|------|------|------|
| `{{age_month}}` | `ctx['baby_age_months']` | |
| `{{avg_sleep}}` | `ctx['this_week']['avg_sleep_h']` | |
| `{{wake_count}}` | `ctx['this_week']['cry_count']` | "야간 각성 횟수" → "울음 감지 횟수"로 명칭 변경 |
| `{{temperature}}` | `ctx['this_week']['temp_avg']` | |
| `{{pattern_summary}}` | `_build_pattern_summary()` 결과 | 신규 |

> `{{bed_time}}` 변수는 제거됨 — DB에 취침 시각 필드가 없어 항상 "미제공"이었으므로 의미 없는 정보 전달을 차단.

---

### output_format.md — JSON 출력 형식 + 최종 규칙

기존 `system_prompt.md`에서 출력 형식 + 규칙 섹션만 남긴 파일.

**변경 포인트:**
- `sleep_guide`에 `kick_action` 필드 신규 추가

```json
"sleep_guide": {
  "method_name": "...",
  "title": "...",
  "reason": "...",
  "steps": ["1단계", "2단계", "3단계"],
  "kick_action": "오늘 밤 바로 ___ 해보세요"   ← 신규
}
```

---

## 4. 코드 변경 사항

### gemini_client.py

**프롬프트 로딩 방식 변경:**

```python
# 변경 전
_PROMPT_PATH   = Path(__file__).parent / "prompts" / "system_prompt.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

# 변경 후
_PROMPTS_DIR = Path(__file__).parent / "prompts"

_SYSTEM_FILES = ["system.md", "knowledge.md", "age_policy.md", "reasoning.md"]

_SYSTEM_PROMPT = (
    "\n\n---\n\n".join(
        (_PROMPTS_DIR / f).read_text(encoding="utf-8") for f in _SYSTEM_FILES
    )
    + "\n\n---\n\n"
    + (_PROMPTS_DIR / "output_format.md").read_text(encoding="utf-8")
)
_INPUT_TEMPLATE = (_PROMPTS_DIR / "input_template.md").read_text(encoding="utf-8")
```

**`_build_prompt()` 변경:**  
하드코딩된 문자열 조합 → `input_template.md` 변수 치환 후 상세 데이터 append 방식으로 변경.

**`_SLEEP_GUIDE_FIELDS` 검증에 `kick_action` 추가:**
```python
_SLEEP_GUIDE_FIELDS = ["method_name", "title", "reason", "steps", "kick_action"]
```

---

### schemas.py

`SleepGuide` 모델에 `kick_action` 필드 추가:

```python
class SleepGuide(BaseModel):
    method_name: str
    title: str
    reason: str
    steps: List[str]
    kick_action: Optional[str] = None   # 신규
```

---

### report_service.py

`_build_pattern_summary()` 함수 신규 추가:  
월령 대비 수면량, 뒤척임 수준, 호흡/체온 이상 여부를 한 줄 텍스트로 변환해  
Gemini user prompt의 `{{pattern_summary}}`에 주입한다.

```python
# 출력 예시
"수면 정상 범위 / 뒤척임 과다"
"수면 부족 / 뒤척임 적음 / 미열 주의"
```

---

## 5. AI 호출 흐름 (변경 후)

```
[서버 시작 시 1회]

prompts/system.md
prompts/knowledge.md
prompts/age_policy.md
prompts/reasoning.md
prompts/output_format.md
        ↓ 순서대로 조합
GenerativeModel(system_instruction=조합 결과)

[리포트 요청마다]

report_service._build_ai_context()
        ↓
  {
    baby_age_months, week_label,
    pattern_summary,     ← _build_pattern_summary()로 계산
    this_week: { 수면/환경/호흡/체온 },
    daily: [ 7일치 ],
    last_week (있으면),
    two_weeks_ago (있으면)
  }
        ↓
gemini_client._build_prompt(ctx)
  → input_template.md {{변수}} 치환
  → 상세 데이터 블록 append
        ↓
_call_gemini(user_prompt)   → Gemini 비동기 호출 (최대 3회 재시도)
        ↓
_validate_json()            → kick_action 포함 필드 검증
        ↓
{ ai_comment, sleep_guide(+kick_action), age_kick }
```
