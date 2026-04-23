"""
simulator_service.py — 테스트·개발용 더미 주간 데이터 생성기

목적:
  실제 맘아이 서버가 POST /api/v1/report/generate 로 push하는 형식과
  완전히 동일한 GenerateReportRequest 구조의 더미 데이터를 생성한다.

포함 데이터 (EMTAKE 프로토콜 전체 반영):
  - sleep     : 7일치 수면·뒤척임 (분 단위 정수) — EMTAKE SleepData day_gs/day_pr
  - environment: 실내 온도·소음 — EMTAKE IndoorTemp + dB
  - breath    : 수면 중 호흡수 — EMTAKE Breath
  - body_temp : 수면 중 체온 상승 — EMTAKE Temp
  - monthly   : 월간 집계 — EMTAKE SleepData month_gs/month_pr
  - events    : 울음·카메라 이탈 횟수

더미 데이터 수치 범위는 실제 영유아(생후 6~12개월) 분포를 기준으로 설정.
"""
import random
from datetime import date, timedelta


def make_dummy_week(
    ser_no: str = "MT-00123",
    baby_age_months: int = 8,
    week_start: date | None = None,
) -> dict:
    """
    GenerateReportRequest 와 동일한 구조의 더미 주간 데이터를 반환한다.

    파라미터:
      ser_no           : 테스트용 기기 시리얼 번호
      baby_age_months  : 테스트 월령 (호흡수 정상 범위 기준에 영향)
      week_start       : None이면 이번 주 월요일 자동 계산

    더미 수치 범위:
      수면       : 480~620분 (8시간 ~ 10시간 20분)
      뒤척임     : 5~40분
      실내 온도  : 최저 20.0~22.0°C / 최고 23.5~25.5°C
      소음       : 평균 35~55dB / 최대 평균+0~20dB
      호흡수     : 최소 22~28 / 최대 35~42 / 평균 사이값 (회/분)
      체온       : 최저 36.2~36.5°C / 최고 36.8~37.6°C (정상·미열 주의 범위 포함)
      월간 수면  : 8.0~10.0시간 / 월간 뒤척임: 0.3~0.8시간
    """
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    # 7일치 수면 데이터 (최소·최대 관계 없음, 일별 독립)
    sleep_days = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        sleep_days.append({
            "date": day.isoformat(),
            "sleep_min": random.randint(480, 620),
            "restless_min": random.randint(5, 40),
        })

    # 실내 온도: 최저 < 평균 < 최고 관계 보장
    temp_min = round(random.uniform(20.0, 22.0), 1)
    temp_max = round(random.uniform(23.5, 25.5), 1)
    temp_avg = round(random.uniform(temp_min, temp_max), 1)

    # 소음: 평균 < 최대 관계 보장
    db_avg = random.randint(35, 55)
    db_max = random.randint(db_avg, db_avg + 20)

    # 호흡수: 최소 < 평균 < 최대 관계 보장
    breath_min = random.randint(22, 28)
    breath_max = random.randint(35, 42)
    breath_avg = random.randint(breath_min, breath_max)

    # 체온: 최저 < 평균 < 최고 관계 보장
    body_temp_min = round(random.uniform(36.2, 36.5), 1)
    body_temp_max = round(random.uniform(36.8, 37.6), 1)
    body_temp_avg = round(random.uniform(body_temp_min, body_temp_max), 1)

    return {
        "ser_no": ser_no,
        "baby_age_months": baby_age_months,
        "week_start": week_start.isoformat(),
        "sleep": sleep_days,
        "environment": {
            "temp_avg": temp_avg,
            "temp_max": temp_max,
            "temp_min": temp_min,
            "db_max": db_max,
            "db_avg": db_avg,
        },
        "breath": {
            "breath_min": breath_min,
            "breath_max": breath_max,
            "breath_avg": breath_avg,
        },
        "body_temp": {
            "body_temp_min": body_temp_min,
            "body_temp_max": body_temp_max,
            "body_temp_avg": body_temp_avg,
        },
        "monthly": {
            # 이번 주와 비슷한 수준에서 소폭 변동하는 월간 평균
            "month_sleep_h":    round(random.uniform(8.0, 10.0), 1),
            "month_restless_h": round(random.uniform(0.3, 0.8), 1),
        },
        "events": {
            "cry_count":   random.randint(0, 5),
            "leave_count": random.randint(0, 2),
        },
    }


def make_multi_week_dummy(
    ser_no: str = "MT-00123",
    baby_age_months: int = 8,
    num_weeks: int = 3,
) -> list[dict]:
    """
    N주치 더미 데이터 리스트를 과거→현재 순으로 반환한다.

    사용 목적:
      POST /api/v1/report/generate 를 순서대로 여러 번 호출해
      3주치 트렌드 데이터가 DB에 누적된 시나리오를 테스트할 때 사용.

    사용 예:
      weeks = make_multi_week_dummy(num_weeks=3)
      for w in weeks:
          requests.post(".../generate", json=w)
      # 마지막(3번째) 응답의 trend 블록에 3주 변화량이 포함되어야 함

    반환 순서: 오래된 주 → 최신 주 (시간 순 정렬)
    """
    today = date.today()
    latest_monday = today - timedelta(days=today.weekday())

    result = []
    for w in range(num_weeks - 1, -1, -1):
        # num_weeks-1 주 전부터 이번 주까지 순서대로 생성
        ws = latest_monday - timedelta(weeks=w)
        result.append(make_dummy_week(ser_no, baby_age_months, ws))
    return result
