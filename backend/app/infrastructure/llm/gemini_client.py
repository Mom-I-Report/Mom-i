"""
gemini_client.py — Gemini 3 Flash 비동기 클라이언트

구현된 기능:
  1. async  — generate_content_async() 로 비동기 호출 (Gemini 대기 3~8초 non-blocking)
  2. 재시도  — 최대 5회, 지수 백오프 (5s → 10s → 20s → 40s → 80s)
             429(Rate limit) / 503(Service Unavailable) 모두 재시도 대상
  3. JSON 출력 — response_mime_type: "application/json" + 프롬프트 강제
  4. JSON 검증 — ai_comment / sleep_guide / age_kick 필드 존재 여부 확인
  5. 토큰 로깅 — 매 호출마다 입력·출력·합계 토큰 수 로그 기록 (비용 추적)
"""
import asyncio
import json
import logging
from google import genai
from google.genai import types
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── 클라이언트 초기화 (모듈 로드 시 1회) ────────────────────────────────────

_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# ── 프롬프트 파일 경로 ────────────────────────────────────────────────────────
_PROMPTS_DIR = Path(__file__).parent / "prompts"

_SYSTEM_FILES = [
    "system.md",        # 역할, HARD RULES, STYLE
    "knowledge.md",     # 판단 기준 (수면/호흡/체온/수면법)
    "reasoning.md",     # 추론 규칙
]

_SYSTEM_PROMPT = (
    "\n\n---\n\n".join(
        (_PROMPTS_DIR / f).read_text(encoding="utf-8") for f in _SYSTEM_FILES
    )
    + "\n\n---\n\n"
    + (_PROMPTS_DIR / "output_format.md").read_text(encoding="utf-8")
)
_INPUT_TEMPLATE = (_PROMPTS_DIR / "input_template.md").read_text(encoding="utf-8")

_MODEL_NAME = "gemini-3.1-flash-lite"

# ── 상수 ─────────────────────────────────────────────────────────────────────

# JSON 응답에 반드시 포함되어야 하는 최상위 필드
_REQUIRED_FIELDS = ["ai_comment", "sleep_guide", "age_kick", "parent_message"]

# sleep_guide 필수 하위 필드
_SLEEP_GUIDE_FIELDS = ["method_name", "title", "reason", "steps", "kick_action"]

# age_kick 필수 하위 필드
_AGE_KICK_FIELDS = ["title", "text", "is_wonder_weeks"]

_MAX_ATTEMPTS   = 5
_BACKOFF_BASE   = 5.0
_RETRYABLE_KEYWORDS = ("429", "quota", "rate", "503", "unavailable")

# 원더윅스 기준 주령 (±1주 이내 → is_wonder_weeks=true)
_WONDER_WEEKS = {5, 8, 12, 19, 26, 37, 46, 55, 64, 75}

# 월령별 허용 수면법 (age_policy.md 대체 — 호출 시 해당 월령만 주입)
_AGE_SLEEP_POLICY: list[tuple[int, str | None]] = [
    (2,   None),                                  # 수면 교육 금지
    (4,   "쉬닥법, 안눈법"),
    (6,   "쉬닥법, 퍼버법(초기), 픽업앤다운"),
    (9,   "퍼버법, 쉬닥법, 픽업앤다운"),
    (12,  "퍼버법 중심, 루틴 강화"),
    (999, "퍼버법, 의자법, 루틴 일관성"),
]


def _get_sleep_policy(age_months: int) -> str | None:
    for max_age, methods in _AGE_SLEEP_POLICY:
        if age_months <= max_age:
            return methods
    return _AGE_SLEEP_POLICY[-1][1]


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in _RETRYABLE_KEYWORDS)


def _validate_json(data: dict) -> list[str]:
    """JSON 구조에서 누락된 필드 목록을 반환한다."""
    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if "ai_comment" in data and not isinstance(data["ai_comment"], list):
        missing.append("ai_comment (list 타입이어야 함)")
    if "sleep_guide" in data and isinstance(data["sleep_guide"], dict):
        missing += [f"sleep_guide.{f}" for f in _SLEEP_GUIDE_FIELDS if f not in data["sleep_guide"]]
    if "age_kick" in data and isinstance(data["age_kick"], dict):
        missing += [f"age_kick.{f}" for f in _AGE_KICK_FIELDS if f not in data["age_kick"]]
    if "parent_message" in data and not isinstance(data["parent_message"], str):
        missing.append("parent_message (string 타입이어야 함)")
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
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
    )
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = await _client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=prompt,
                config=config,
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
        "ai_comment": [{"type": "caution"|"good", "icon": "🌡️", "title": "...", "text": "..."}],
        "sleep_guide": {
            "method_name": "퍼버법",
            "title": "✨ 추천 솔루션: ...",
            "reason": "...",
            "steps": ["1단계 ...", "2단계 ...", "3단계 ..."]
        },
        "age_kick": {
            "title": "8개월 분리불안",
            "text": "...",
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
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("[Gemini] 재호출 후에도 JSON 파싱 실패 — 원본: %s", raw[:200])
            raise

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
    """
    4_INPUT.md.txt 템플릿을 기반으로 변수를 치환한 뒤
    상세 데이터 블록(환경·호흡·체온·일별·트렌드)을 추가해 최종 user prompt를 반환한다.
    """
    tw = ctx["this_week"]

    # ── 주령 계산 + 사전 판정 ────────────────────────────────────────────────
    age_months    = ctx["baby_age_months"]
    age_weeks     = round(age_months * 4.3)
    is_ww         = any(abs(age_weeks - ww) <= 1 for ww in _WONDER_WEEKS)
    sleep_policy  = _get_sleep_policy(age_months)
    policy_text   = (
        "없음 (0~2개월 — sleep_guide는 반드시 null)"
        if sleep_policy is None else sleep_policy
    )

    # ── 4_INPUT 템플릿 변수 치환 ─────────────────────────────────────────────
    prompt = (
        _INPUT_TEMPLATE
        .replace("{{age_month}}",       f"{age_months}개월 (약 {age_weeks}주령)")
        .replace("{{avg_sleep}}",       f"{tw['avg_sleep_h']}시간")
        .replace("{{wake_count}}",      f"{tw['cry_count']}회")
        .replace("{{temperature}}",     f"평균 {tw['temp_avg']}°C")
        .replace("{{pattern_summary}}", ctx.get("pattern_summary", ""))
    )
    prompt += f"\n허용 수면법: {policy_text}\n원더윅스 해당: {'true' if is_ww else 'false'}"

    # ── 상세 데이터 블록 ─────────────────────────────────────────────────────
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

    # 실내 온도 판정 (권장 18~22°C, 신생아 20~22°C)
    temp_lo, temp_hi = (20.0, 22.0) if age_months <= 3 else (18.0, 22.0)
    if tw["temp_max"] > temp_hi + 2:
        indoor_temp_note = f" ⚠ 최고 {tw['temp_max']}°C — 권장({temp_lo}~{temp_hi}°C) 초과"
    elif tw["temp_min"] < temp_lo - 3:
        indoor_temp_note = f" ⚠ 최저 {tw['temp_min']}°C — 권장({temp_lo}~{temp_hi}°C) 미만"
    else:
        indoor_temp_note = f" ✅ 권장 범위 ({temp_lo}~{temp_hi}°C) 내"

    # 취침 시간 판정 (knowledge 기준)
    def _bedtime_note(daily: list) -> str:
        night_starts = [
            d["night_sessions"][0]["start"]
            for d in daily if d.get("night_sessions")
        ]
        if not night_starts:
            return ""
        def to_min(t: str) -> int:
            h, m = map(int, t.split(":"))
            return h * 60 + m
        avg_start = round(sum(to_min(t) for t in night_starts) / len(night_starts))
        h, m = divmod(avg_start, 60)
        if age_months <= 8:
            rec_lo, rec_hi = 18 * 60, 20 * 60
        elif age_months <= 23:
            rec_lo, rec_hi = 19 * 60, 20 * 60 + 30
        else:
            rec_lo, rec_hi = 19 * 60 + 30, 21 * 60
        note = f" (평균 취침 {h:02d}:{m:02d}"
        if avg_start > rec_hi:
            over = avg_start - rec_hi
            note += f" — 권장보다 {over//60}시간 {over%60}분 늦음 ⚠)"
        elif avg_start < rec_lo:
            note += " — 권장보다 빠름 ✅)"
        else:
            note += " — 권장 시간대 ✅)"
        return note
    bedtime_note = _bedtime_note(ctx.get("daily", []))

    # 일별 수면 라인 생성
    day_lines_list = []
    for d in ctx.get("daily", []):
        line = f"  {d['day']}: 수면 {d['sleep_h']}h / 뒤척임 {d['restless_min']}분"
        if d.get("wakeup_count") is not None:
            line += f" / 총뒤척임 {d['wakeup_count']}회"
        if d.get("nap_sessions", 0) > 0:
            line += f" / 낮잠 {d['nap_sessions']}회"
        if d.get("night_sessions"):
            ns = d["night_sessions"]
            if ns:
                ns0 = ns[0]
                line += f" / 밤잠 {ns0['start']}~{ns0['end']}({ns0['duration_min']}분)"
        if d.get("device_status") and d["device_status"] != "NORMAL":
            line += f" [{d['device_status']}]"
        day_lines_list.append(line)
    day_lines = "\n".join(day_lines_list)

    # 환경 부가 정보 (습도, 조도)
    env_extra = ""
    if tw.get("humidity_avg") is not None:
        hum_note = ""
        hum_avg = tw["humidity_avg"]
        if hum_avg < 40:
            hum_note = " ⚠ 건조"
        elif hum_avg > 60:
            hum_note = " ⚠ 과습"
        env_extra += f" / 습도 평균 {hum_avg}% (최소 {tw.get('humidity_min')} / 최대 {tw.get('humidity_max')}){hum_note}"
    if tw.get("bright_avg") is not None:
        bright_avg = tw["bright_avg"]
        bright_note = ""
        if bright_avg > 20:
            bright_note = " ⚠ 수면 중 밝음 (5lux 이하 권장)"
        elif bright_avg > 5:
            bright_note = " △ 약간 밝음"
        env_extra += f" / 조도 평균 {bright_avg}lux (최소 {tw.get('bright_min')} / 최대 {tw.get('bright_max')}){bright_note}"

    # 주간/낮잠 요약
    weekly_extra = ""
    if tw.get("week_sleep_h") is not None:
        weekly_extra += f" / 주간 평균 수면 {tw['week_sleep_h']}h"
    if tw.get("week_restless_h") is not None:
        weekly_extra += f" / 주간 평균 뒤척임 {tw['week_restless_h']}h"
    if tw.get("nap_count") is not None:
        weekly_extra += f" / 주간 낮잠 {tw['nap_count']}회"

    prompt += f"""

[상세 데이터]
주간: 뒤척임 {tw['avg_restless_min']}분 / 월간 평균 수면 {tw['month_sleep_h']}h{weekly_extra}
환경: 온도 {tw['temp_avg']}°C (최고 {tw['temp_max']} / 최저 {tw['temp_min']}){indoor_temp_note} / 소음 최고 {tw['db_max']}dB (릴레이 Max값만 제공){env_extra}
호흡: 평균 {tw['breath_avg']}회/분 (최소 {tw['breath_min']} / 최대 {tw['breath_max']}) — {breath_status}
체온: 평균 {tw['body_temp_avg']}°C / 최고 {tw['body_temp_max']}°C — {tw['body_temp_status']}{temp_extra}

[일별 수면]{bedtime_note}
{day_lines}
"""

    if "last_week" in ctx:
        lw = ctx["last_week"]
        prompt += f"""
[지난 주 대비]
수면: {lw['avg_sleep_h']}h → {tw['avg_sleep_h']}h / 뒤척임: {lw['avg_restless_min']}분 → {tw['avg_restless_min']}분
울음: {lw['cry_count']}회 → {tw['cry_count']}회 / 호흡: {lw['breath_avg']}회/분 → {tw['breath_avg']}회/분
체온: {lw['body_temp_avg']}°C → {tw['body_temp_avg']}°C (최고: {lw['body_temp_max']}°C → {tw['body_temp_max']}°C)
"""

    if "two_weeks_ago" in ctx:
        ww = ctx["two_weeks_ago"]
        prompt += f"""
[2주 전]
수면 {ww['avg_sleep_h']}h / 뒤척임 {ww['avg_restless_min']}분 / 울음 {ww['cry_count']}회
호흡: {ww['breath_avg']}회/분 / 체온: {ww['body_temp_avg']}°C
"""

    prompt += "\n위 데이터를 바탕으로 시스템 프롬프트에 정의된 JSON 구조로 응답하라. 반드시 유효한 JSON만 출력하라."
    return prompt
