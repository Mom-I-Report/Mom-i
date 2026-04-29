"""
emtake/client.py — EMTAKE relay API 비동기 클라이언트

엔드포인트: POST http://relay.emtake.com/api/query
필수 파라미터: Type="LLMREPORT", Account(이메일), UID(시리얼), CMD

현재 확인된 CMD (2026-04-28 기준):
  SleepData : day_gs/day_pr(오늘), week_gs/week_pr(주간평균), month_gs/month_pr(월간평균)

목요일(2026-04-30) 추가 예정:
  - 아이 정보 (생년월일 → baby_age_months)
  - 7일치 날짜별 수면 상세 (우리 서버 sleep[7] 구성에 필수)
  - CMD: Breath  (호흡수 — breath_min/max/avg)
  - CMD: Temp    (체온 상승 — body_temp_min/max/avg)
  - CMD: IndoorTemp + dB (실내 온도·소음 — environment)
  - 이벤트 데이터 (울음·이탈 횟수 — events)

응답 포맷:
  엔드포인트는 JSON 문자열을 문자열로 감싸 반환하는 경우가 있어
  이중 파싱(json.loads × 2)을 안전하게 처리한다.
"""
import json
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_EMTAKE_URL = "http://relay.emtake.com/api/query"
_REQUEST_TIMEOUT = 10.0


# ── 파싱 유틸 ────────────────────────────────────────────────────────────────

def parse_duration_str(s: str) -> int:
    """
    EMTAKE 시간 문자열을 분(int)으로 변환한다.

    지원 형식:
      "4h50m" → 290   "3h" → 180   "50m" → 50   "1h05m" → 65
    """
    s = s.strip()
    h = int(m.group(1)) if (m := re.search(r"(\d+)h", s)) else 0
    mn = int(m.group(1)) if (m := re.search(r"(\d+)m", s)) else 0
    return h * 60 + mn


def _parse_response(raw: str | dict) -> dict:
    """
    API 응답이 dict이면 그대로, 문자열이면 JSON 파싱해 반환한다.
    일부 엔드포인트가 JSON을 문자열로 한번 더 감싸 반환하는 경우를 처리한다.
    """
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


# ── 저수준 HTTP 호출 ─────────────────────────────────────────────────────────

async def _fetch_raw(account: str, uid: str, cmd: str) -> dict:
    """
    EMTAKE relay API를 비동기로 호출하고 dict를 반환한다.

    파라미터:
      account : 맘아이 계정 이메일 (예: "test1@test1.com")
      uid     : 기기 시리얼 번호 (예: "SERIAL")
      cmd     : 데이터 종류 (예: "SleepData", "Breath", "Temp")
    """
    payload = {
        "Type":    "LLMREPORT",
        "Account": account,
        "UID":     uid,
        "CMD":     cmd,
    }
    logger.debug("[EMTAKE] 요청 — CMD=%s account=%s uid=%s", cmd, account, uid)

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        response = await client.post(_EMTAKE_URL, json=payload)
        response.raise_for_status()

    raw = response.json()
    data = _parse_response(raw)
    logger.debug("[EMTAKE] 응답 — CMD=%s data=%s", cmd, data)
    return data


# ── CMD별 고수준 함수 ────────────────────────────────────────────────────────

async def fetch_sleep_data(account: str, uid: str) -> dict:
    """
    CMD: SleepData — 수면 집계값을 파싱해 분·시간 단위로 반환한다.

    EMTAKE 원본:
      day_gs / day_pr   : 오늘 수면·뒤척임 (예: "4h50m")
      week_gs / week_pr : 주간 평균 수면·뒤척임
      month_gs / month_pr : 월간 평균 수면·뒤척임

    반환 (분 단위 정수 / 시간 단위 float):
      {
        "day_sleep_min":     290,    # 오늘 수면 (분)
        "day_restless_min":  115,    # 오늘 뒤척임 (분)
        "week_sleep_min":    230,    # 주간 평균 수면 (분)
        "week_restless_min": 170,    # 주간 평균 뒤척임 (분)
        "month_sleep_h":     3.75,   # 월간 평균 수면 (시간)
        "month_restless_h":  1.5,    # 월간 평균 뒤척임 (시간)
      }

    현재 한계:
      오늘/주간/월간 집계값만 제공 → 7일치 날짜별 SleepDay 배열 구성 불가.
      날짜별 데이터는 목요일(2026-04-30) 추가 예정 CMD로 보완 예정.
    """
    raw = await _fetch_raw(account, uid, "SleepData")
    return {
        "day_sleep_min":     parse_duration_str(raw["day_gs"]),
        "day_restless_min":  parse_duration_str(raw["day_pr"]),
        "week_sleep_min":    parse_duration_str(raw["week_gs"]),
        "week_restless_min": parse_duration_str(raw["week_pr"]),
        "month_sleep_h":     round(parse_duration_str(raw["month_gs"]) / 60, 2),
        "month_restless_h":  round(parse_duration_str(raw["month_pr"]) / 60, 2),
    }


# ── 목요일(2026-04-30) 추가 예정 CMD 함수 시그니처 ──────────────────────────
#
# async def fetch_baby_info(account: str, uid: str) -> dict:
#     """
#     아이 정보 (생년월일 → baby_age_months 계산).
#     반환 예시: {"baby_age_months": 8, "birth_date": "2025-08-01"}
#     """
#
# async def fetch_sleep_daily(account: str, uid: str) -> list[dict]:
#     """
#     7일치 날짜별 수면 상세. GenerateReportRequest.sleep[7] 구성에 필수.
#     반환 예시: [{"date": "2026-04-21", "sleep_min": 540, "restless_min": 20}, ...]
#     """
#
# async def fetch_breath(account: str, uid: str) -> dict:
#     """
#     CMD: Breath — 수면 중 호흡수 (회/분).
#     반환 예시: {"breath_min": 22, "breath_max": 38, "breath_avg": 30}
#     """
#
# async def fetch_body_temp(account: str, uid: str) -> dict:
#     """
#     CMD: Temp — 수면 중 체온 상승 (°C).
#     반환 예시: {"body_temp_min": 36.2, "body_temp_max": 37.1, "body_temp_avg": 36.6}
#     """
#
# async def fetch_environment(account: str, uid: str) -> dict:
#     """
#     CMD: IndoorTemp + dB — 실내 온도·소음 집계.
#     반환 예시: {"temp_avg": 23.0, "temp_max": 25.0, "temp_min": 21.0,
#                 "db_avg": 40, "db_max": 58}
#     """
#
# async def fetch_events(account: str, uid: str) -> dict:
#     """
#     울음 감지·카메라 이탈 횟수.
#     반환 예시: {"cry_count": 2, "leave_count": 1}
#     """
