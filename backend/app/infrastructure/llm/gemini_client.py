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


def generate_insight(data: dict) -> str:
    """
    7일치 집계 데이터를 받아 Gemini가 인사이트 코멘트를 생성합니다.

    data 예시:
    {
        "baby_name": "민준",
        "baby_age_months": 8,
        "week_label": "2025년 4월 2주차",
        "avg_sleep_h": 9.2,
        "avg_restless_min": 18,
        "temp_avg": 23.1,
        "db_max": 62,
        "cry_count": 3,
        "leave_count": 1,
        "daily_summary": "월 9.5h / 화 8.8h / ..."
    }
    """
    prompt = f"""
아래는 {data['baby_name']} 아기({data['baby_age_months']}개월)의 {data['week_label']} 수면 데이터입니다.

[ 주간 요약 ]
- 평균 수면 시간: {data['avg_sleep_h']}시간
- 평균 뒤척임: {data['avg_restless_min']}분
- 평균 실내 온도: {data['temp_avg']}°C
- 최대 소음: {data['db_max']}dB
- 울음 이벤트: {data['cry_count']}회
- 카메라 이탈: {data['leave_count']}회

[ 일별 수면 시간 ]
{data['daily_summary']}

위 데이터를 바탕으로 부모에게 전달할 수면 분석 코멘트를 3~5문장으로 작성해줘.
따뜻하고 전문적인 톤으로, 아이 이름을 자연스럽게 넣어줘.
"""
    response = _model.generate_content(prompt)
    return response.text.strip()
