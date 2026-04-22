"""
gemini_client.py — Gemini 2.5 Flash 비동기 클라이언트

구현된 기능:
  1. async  — generate_content_async() 로 비동기 호출 (Gemini 대기 3~8초 non-blocking)
  2. 재시도  — 최대 3회, 지수 백오프 (1s → 2s → 4s)
             429(Rate limit) / 503(Service Unavailable) 모두 재시도 대상
  3. JSON 출력 — response_mime_type: "application/json" + 프롬프트 강제
  4. JSON 검증 — ai_comment / sleep_guide / age_kick 필드 존재 여부 확인
  5. 토큰 로깅 — 매 호출마다 입력·출력·합계 토큰 수 로그 기록 (비용 추적)
  6. Thinking budget — 1024 토큰으로 제한 (추론 품질 유지 + 속도 균형)
"""
import asyncio
import json
import logging
import google.generativeai as genai
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── 모델 초기화 (모듈 로드 시 1회) ──────────────────────────────────────────

genai.configure(api_key=settings.GEMINI_API_KEY)

_PROMPT_PATH   = Path(__file__).parent / "prompts" / "system_prompt.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=_SYSTEM_PROMPT,
)

# ── 상수 ─────────────────────────────────────────────────────────────────────

# JSON 응답에 반드시 포함되어야 하는 최상위 필드
_REQUIRED_FIELDS = ["ai_comment", "sleep_guide", "age_kick"]

# sleep_guide 필수 하위 필드
_SLEEP_GUIDE_FIELDS = ["method_name", "reason", "tonight_guide", "caution"]

# age_kick 필수 하위 필드
_AGE_KICK_FIELDS = ["title", "description", "tip", "is_wonder_weeks"]

_THINKING_BUDGET = 1024
_MAX_ATTEMPTS   = 3
_BACKOFF_BASE   = 1.0
_RETRYABLE_KEYWORDS = ("429", "quota", "rate", "503", "unavailable")


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in _RETRYABLE_KEYWORDS)


def _validate_json(data: dict) -> list[str]:
    """JSON 구조에서 누락된 필드 목록을 반환한다."""
    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if "sleep_guide" in data and isinstance(data["sleep_guide"], dict):
        missing += [f"sleep_guide.{f}" for f in _SLEEP_GUIDE_FIELDS if f not in data["sleep_guide"]]
    if "age_kick" in data and isinstance(data["age_kick"], dict):
        missing += [f"age_kick.{f}" for f in _AGE_KICK_FIELDS if f not in data["age_kick"]]
    return missing


def _log_token_usage(response) -> None:
    try:
        meta = response.usage_metadata
        logger.info(
            "[Gemini 토큰] 입력: %d / 출력: %d / 합계: %d",
            meta.prompt_token_count,
            meta.candidates_token_count,
            meta.total_token_count,
        )
    except Exception:
        logger.debug("[Gemini 토큰] usage_metadata 접근 실패 — 로깅 스킵")


async def _call_gemini(prompt: str) -> str:
    """
    Gemini를 비동기로 호출하고 응답 텍스트를 반환한다.
    response_mime_type: "application/json" 으로 JSON 출력을 강제한다.
    """
    generation_config = {
        "response_mime_type": "application/json",
        "thinking_config": {"thinking_budget": _THINKING_BUDGET},
    }
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = await _model.generate_content_async(
                prompt,
                generation_config=generation_config,
            )
            _log_token_usage(response)
            return response.text.strip()

        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == _MAX_ATTEMPTS:
                raise

            wait = _BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(
                "[Gemini] 호출 실패 (시도 %d/%d) — %s / %.0f초 후 재시도",
                attempt, _MAX_ATTEMPTS, exc, wait,
            )
            await asyncio.sleep(wait)

    raise last_exc


# ── Public API ───────────────────────────────────────────────────────────────

async def generate_insight(ctx: dict) -> dict:
    """
    최대 3주치 수면·호흡·체온 컨텍스트를 받아 Gemini JSON 리포트를 생성한다.

    반환 구조:
    {
        "ai_comment": "이번 주 총평 텍스트",
        "sleep_guide": {
            "method_name": "퍼버법",
            "reason": "...",
            "tonight_guide": "...",
            "caution": "..."
        },
        "age_kick": {
            "title": "8개월 분리불안",
            "description": "...",
            "tip": "...",
            "is_wonder_weeks": true
        }
    }

    처리 흐름:
      1. 프롬프트 조립
      2. Gemini 비동기 호출 (재시도 포함)
      3. JSON 파싱
      4. 필드 검증 → 누락 시 보정 재호출
      5. dict 반환
    """
    prompt = _build_prompt(ctx)
    raw = await _call_gemini(prompt)

    # JSON 파싱
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("[Gemini] JSON 파싱 실패 — 재호출: %s", raw[:200])
        fix_prompt = prompt + "\n\n[주의] 반드시 유효한 JSON만 출력하라. 마크다운 코드 블록 없이 순수 JSON."
        raw = await _call_gemini(fix_prompt)
        data = json.loads(raw)

    # 필드 검증
    missing = _validate_json(data)
    if missing:
        logger.warning("[Gemini] 필드 누락 %s — 보정 재호출", missing)
        fix_prompt = (
            prompt
            + f"\n\n[주의] 아래 필드가 누락되었습니다. 반드시 포함해서 다시 출력하라:\n"
            + "\n".join(missing)
        )
        raw = await _call_gemini(fix_prompt)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("[Gemini] 보정 후 JSON 파싱 실패 — 현재 결과 반환")

        still_missing = _validate_json(data)
        if still_missing:
            logger.error("[Gemini] 보정 후에도 필드 누락 %s — 현재 결과 반환", still_missing)

    return data


def _build_prompt(ctx: dict) -> str:
    """AI 컨텍스트 dict를 Gemini 사용자 프롬프트 문자열로 변환한다."""
    tw = ctx["this_week"]

    day_lines = "\n".join(
        f"  {d['day']}: 수면 {d['sleep_h']}h / 뒤척임 {d['restless_min']}분"
        for d in ctx.get("daily", [])
    )

    breath_status = (
        f"정상 범위 내 ({tw['breath_normal_range']})"
        if tw["breath_is_normal"]
        else f"⚠ 정상 범위 벗어남 (정상: {tw['breath_normal_range']})"
    )

    temp_extra = {
        "정상":      "",
        "미열 주의": " → 수면 환경 온도·보온 상태 확인 권장",
        "발열 의심": " → 소아과 상담 권장",
    }.get(tw["body_temp_status"], "")

    prompt = f"""
생후 {ctx['baby_age_months']}개월 아기의 {ctx['week_label']} 수면 데이터입니다.

[주간 수면 요약]
- 이번 주 평균 수면: {tw['avg_sleep_h']}시간 / 이번 주 평균 뒤척임: {tw['avg_restless_min']}분
- 월간 평균 수면: {tw['month_sleep_h']}시간 / 월간 평균 뒤척임: {tw['month_restless_h']}시간
- 울음: {tw['cry_count']}회 / 카메라 이탈: {tw['leave_count']}회

[실내 환경]
- 온도: 평균 {tw['temp_avg']}°C (최고 {tw['temp_max']}° / 최저 {tw['temp_min']}°)
- 소음: 평균 {tw['db_avg']}dB / 최대 {tw['db_max']}dB

[호흡수 분석]
- 수면 중 평균 호흡수: {tw['breath_avg']}회/분 (최소 {tw['breath_min']} / 최대 {tw['breath_max']})
- 판정: {breath_status}

[체온 분석]
- 수면 중 평균 체온: {tw['body_temp_avg']}°C / 최고 {tw['body_temp_max']}°C
- 상태: {tw['body_temp_status']}{temp_extra}

[일별 수면]
{day_lines}
"""

    if "last_week" in ctx:
        lw = ctx["last_week"]
        prompt += f"""
[지난 주 대비]
- 수면: {lw['avg_sleep_h']}h → {tw['avg_sleep_h']}h
- 뒤척임: {lw['avg_restless_min']}분 → {tw['avg_restless_min']}분
- 울음: {lw['cry_count']}회 → {tw['cry_count']}회
- 호흡수(평균): {lw['breath_avg']}회/분 → {tw['breath_avg']}회/분
- 체온(평균): {lw['body_temp_avg']}°C → {tw['body_temp_avg']}°C (최고: {lw['body_temp_max']}°C → {tw['body_temp_max']}°C)
"""

    if "two_weeks_ago" in ctx:
        ww = ctx["two_weeks_ago"]
        prompt += f"""
[2주 전]
- 수면 {ww['avg_sleep_h']}h / 뒤척임 {ww['avg_restless_min']}분 / 울음 {ww['cry_count']}회
- 호흡수(평균): {ww['breath_avg']}회/분 / 체온(평균): {ww['body_temp_avg']}°C
"""

    prompt += """
위 데이터를 바탕으로 시스템 프롬프트에 정의된 JSON 구조로 응답하라.
반드시 유효한 JSON만 출력하라. 마크다운 코드 블록 없이 순수 JSON.
"""
    return prompt
