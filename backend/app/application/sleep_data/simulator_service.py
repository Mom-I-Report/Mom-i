"""
수면 데이터 시뮬레이터 — 테스트/개발용 더미 주간 데이터 생성기

실제 맘아이 서버가 POST /api/v1/report/generate 로 push 하는 형식과 동일한
GenerateReportRequest 구조의 더미 데이터를 만들어 반환한다.
"""
import random
from datetime import date, timedelta


def make_dummy_week(
    ser_no: str = "MT-00123",
    baby_age_months: int = 8,
    week_start: date | None = None,
) -> dict:
    """
    GenerateReportRequest 와 동일한 구조의 더미 주간 데이터 반환.

    반환 예시:
    {
        "ser_no": "MT-00123",
        "baby_age_months": 8,
        "week_start": "2026-04-07",
        "sleep": [
            {"date": "2026-04-07", "sleep_min": 562, "restless_min": 18},
            ...  (7일치)
        ],
        "environment": {
            "temp_avg": 22.8, "temp_max": 24.1, "temp_min": 21.3,
            "db_max": 58, "db_avg": 44
        },
        "events": {"cry_count": 2, "leave_count": 1}
    }
    """
    if week_start is None:
        # 이번 주 월요일
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    sleep_days = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        sleep_days.append({
            "date": day.isoformat(),
            "sleep_min": random.randint(480, 620),   # 8h ~ 10h20m
            "restless_min": random.randint(5, 40),
        })

    return {
        "ser_no": ser_no,
        "baby_age_months": baby_age_months,
        "week_start": week_start.isoformat(),
        "sleep": sleep_days,
        "environment": {
            "temp_avg": round(random.uniform(21.0, 24.0), 1),
            "temp_max": round(random.uniform(23.5, 25.5), 1),
            "temp_min": round(random.uniform(20.0, 22.0), 1),
            "db_max": random.randint(50, 70),
            "db_avg": random.randint(35, 55),
        },
        "events": {
            "cry_count": random.randint(0, 5),
            "leave_count": random.randint(0, 2),
        },
    }


def make_multi_week_dummy(
    ser_no: str = "MT-00123",
    baby_age_months: int = 8,
    num_weeks: int = 3,
) -> list[dict]:
    """
    num_weeks 주치 더미 데이터 리스트 반환 (최근 순).
    POST /api/v1/report/generate 를 여러 번 호출하는 시나리오 테스트에 사용.
    """
    today = date.today()
    latest_monday = today - timedelta(days=today.weekday())

    result = []
    for w in range(num_weeks - 1, -1, -1):
        ws = latest_monday - timedelta(weeks=w)
        result.append(make_dummy_week(ser_no, baby_age_months, ws))
    return result
