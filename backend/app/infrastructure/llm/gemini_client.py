import google.generativeai as genai
from pathlib import Path
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=_SYSTEM_PROMPT,
)


def generate_insight(ctx: dict) -> str:
    """
    최대 3주치 수면 컨텍스트를 받아 Gemini가 한국어 육아 조언을 생성합니다.

    ctx 구조:
    {
        "baby_age_months": 8,
        "week_label": "2026년 4월 2주차",
        "this_week": {
            "avg_sleep_h": 9.1, "avg_restless_min": 25,
            "cry_count": 3, "temp_avg": 23.1, "db_max": 62
        },
        "last_week":     { ... },   # 있으면 포함
        "two_weeks_ago": { ... },   # 있으면 포함
    }
    """
    tw  = ctx["this_week"]
    day_lines = "\n".join(
        f"  {d['day']}: 수면 {d['sleep_h']}h / 뒤척임 {d['restless_min']}분"
        for d in ctx.get("daily", [])
    )

    prompt = f"""
생후 {ctx['baby_age_months']}개월 아기의 {ctx['week_label']} 수면 데이터입니다.

[주간 요약]
- 평균 수면: {tw['avg_sleep_h']}시간 / 평균 뒤척임: {tw['avg_restless_min']}분
- 울음: {tw['cry_count']}회 / 카메라 이탈: {tw['leave_count']}회
- 온도: 평균 {tw['temp_avg']}°C (최고 {tw['temp_max']}° / 최저 {tw['temp_min']}°)
- 소음: 평균 {tw['db_avg']}dB / 최대 {tw['db_max']}dB

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
"""

    if "two_weeks_ago" in ctx:
        ww = ctx["two_weeks_ago"]
        prompt += f"""
[2주 전]
- 수면 {ww['avg_sleep_h']}h / 뒤척임 {ww['avg_restless_min']}분 / 울음 {ww['cry_count']}회
"""

    prompt += """
위 데이터를 바탕으로 시스템 프롬프트에 정의된 4개 섹션(### 이번 주 총평 / ### 수면 패턴 분석 / ### 환경 영향 분석 / ### 부모 조언)을 순서대로 작성하라.
"""

    response = _model.generate_content(prompt)
    return response.text.strip()
