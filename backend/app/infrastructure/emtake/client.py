"""
emtake/client.py — EMTAKE relay API 비동기 클라이언트

엔드포인트: POST http://relay.emtake.com/api/query
필수 파라미터: Type, Account(이메일), UID(시리얼), CMD

Type 구분:
  LLMREPORT  : 유아 데이터 (기본값)
  LLMREPORTS : 시니어 데이터

선택 파라미터:
  val  : 마지막 저장일로부터 N일 전 데이터 (예: val=5 → -5일)
  date : 특정 날짜 데이터 (예: "2026-04-30")

확인된 CMD:
  SleepData  : day_gs/day_pr(오늘), week_gs/week_pr(주간평균), month_gs/month_pr(월간평균)
  Breath     : 수면 중 호흡수 Min/Max
  Temp       : 수면 중 체온 상승 Min/Max (절대값 아닌 델타값)
  IndoorTemp : 실내 온도 Min/Max
  dB         : 실내 소음 Min/Max
  BabyInfo   : 아이 정보 (생년월일 포함)
  Events     : 울음 감지·카메라 이탈 횟수

응답 포맷:
  엔드포인트는 JSON 문자열을 문자열로 감싸 반환하는 경우가 있어
  이중 파싱(json.loads × 2)을 안전하게 처리한다.

주의:
  - Temp(체온)는 절대 체온이 아닌 기준값 대비 상승분(델타)이다.
  - Breath/Temp/IndoorTemp/dB 는 Min/Max 만 제공 → avg = (Min + Max) / 2 로 계산.
  - BabyInfo 응답의 생년월일은 baby_age_months 계산에만 사용하고 개인정보는 저장하지 않는다.
"""
import json
import logging
import re
from datetime import date as date_cls
from typing import Optional

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
    빈 문자열이나 파싱 불가한 값은 0 반환.
    """
    if not s:
        return 0
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


def _calc_avg_int(min_val: int, max_val: int) -> int:
    return round((min_val + max_val) / 2)


def _calc_avg_float(min_val: float, max_val: float, ndigits: int = 2) -> float:
    return round((min_val + max_val) / 2, ndigits)


def _calc_age_months(birth_date_str: str) -> int:
    """생년월일 문자열(ISO 형식)로부터 현재 월령을 계산한다."""
    try:
        birth = date_cls.fromisoformat(birth_date_str[:10])
        today = date_cls.today()
        return (today.year - birth.year) * 12 + (today.month - birth.month)
    except (ValueError, TypeError):
        logger.warning("[EMTAKE] 생년월일 파싱 실패: %s", birth_date_str)
        return 0


# ── 저수준 HTTP 호출 ─────────────────────────────────────────────────────────

async def _fetch_raw(
    account: str,
    uid: str,
    cmd: str,
    val: Optional[int] = None,
    date_str: Optional[str] = None,
    user_type: str = "LLMREPORT",
) -> dict:
    """
    EMTAKE relay API를 비동기로 호출하고 dict를 반환한다.

    파라미터:
      account   : 맘아이 계정 이메일 (예: "test1@test1.com")
      uid       : 기기 시리얼 번호 (예: "SERIAL")
      cmd       : 데이터 종류 (예: "SleepData", "Breath", "Temp")
      val       : 마지막 저장일로부터 N일 전 데이터 (선택)
      date_str  : 특정 날짜 데이터 "YYYY-MM-DD" (선택, val과 동시 사용 불가)
      user_type : "LLMREPORT"(유아) | "LLMREPORTS"(시니어)
    """
    payload: dict = {
        "Type":    user_type,
        "Account": account,
        "UID":     uid,
        "CMD":     cmd,
    }
    if val is not None:
        payload["val"] = val
    if date_str is not None:
        payload["date"] = date_str

    logger.debug(
        "[EMTAKE] 요청 — CMD=%s account=%s uid=%s val=%s date=%s",
        cmd, account, uid, val, date_str,
    )

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        response = await client.post(_EMTAKE_URL, json=payload)
        response.raise_for_status()

    raw = response.json()
    data = _parse_response(raw)
    logger.debug("[EMTAKE] 응답 — CMD=%s data=%s", cmd, data)
    return data


# ── CMD별 고수준 함수 ────────────────────────────────────────────────────────

async def fetch_sleep_data(account: str, uid: str, user_type: str = "LLMREPORT") -> dict:
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
    """
    raw = await _fetch_raw(account, uid, "SleepData", user_type=user_type)
    return {
        "day_sleep_min":     parse_duration_str(raw.get("day_gs", "")),
        "day_restless_min":  parse_duration_str(raw.get("day_pr", "")),
        "week_sleep_min":    parse_duration_str(raw.get("week_gs", "")),
        "week_restless_min": parse_duration_str(raw.get("week_pr", "")),
        "month_sleep_h":     round(parse_duration_str(raw.get("month_gs", "")) / 60, 2),
        "month_restless_h":  round(parse_duration_str(raw.get("month_pr", "")) / 60, 2),
    }


async def fetch_sleep_daily(
    account: str,
    uid: str,
    val: int,
    ref_date: date_cls,
    user_type: str = "LLMREPORT",
) -> dict:
    """
    CMD: SleepData + val — 특정 날짜(마지막 저장일 기준 -val일)의 수면 데이터를 반환한다.

    val=1 → 어제, val=2 → 이틀 전, ..., val=7 → 7일 전

    반환:
      {
        "date":             "2026-04-28",
        "sleep_min":        290,
        "restless_min":     70,
        "awake_min":        None,      # relay 미지원 시 None
        "deep_sleep_min":   None,
        "rem_sleep_min":    None,
        "light_sleep_min":  None,
        "wake_time_min":    None,
      }
    """
    from datetime import timedelta
    raw = await _fetch_raw(account, uid, "SleepData", val=val, user_type=user_type)
    target_date = ref_date - timedelta(days=val - 1)

    def _opt_dur(key: str) -> Optional[int]:
        v = raw.get(key)
        return parse_duration_str(v) if v else None

    return {
        "date":            str(target_date),
        "sleep_min":       parse_duration_str(raw.get("day_gs", "")),
        "restless_min":    parse_duration_str(raw.get("day_pr", "")),
        "awake_min":       _opt_dur("day_awake"),
        "deep_sleep_min":  _opt_dur("day_deep"),
        "rem_sleep_min":   _opt_dur("day_rem"),
        "light_sleep_min": _opt_dur("day_light"),
        "wake_time_min":   _opt_dur("day_wake"),
    }


async def fetch_baby_info(account: str, uid: str, user_type: str = "LLMREPORT") -> dict:
    """
    아이 정보 조회. 생년월일로 baby_age_months 계산 후 반환.
    개인정보(이름, 성별, 생년월일 원본)는 저장하지 않는다.

    반환:
      {"baby_age_months": 8}
    """
    raw = await _fetch_raw(account, uid, "BabyInfo", user_type=user_type)
    birth = (
        raw.get("birth_date")
        or raw.get("BirthDate")
        or raw.get("birthday")
        or ""
    )
    return {"baby_age_months": _calc_age_months(birth)}


async def fetch_breath(account: str, uid: str, user_type: str = "LLMREPORT") -> dict:
    """
    CMD: Breath — 수면 중 호흡수 (회/분).
    relay는 Min/Max만 제공하므로 avg = (Min + Max) / 2 로 계산한다.

    반환:
      {"breath_min": 22, "breath_max": 38, "breath_avg": 30}
    """
    raw = await _fetch_raw(account, uid, "Breath", user_type=user_type)
    b_min = int(raw.get("Min", 0))
    b_max = int(raw.get("Max", 0))
    return {
        "breath_min": b_min,
        "breath_max": b_max,
        "breath_avg": _calc_avg_int(b_min, b_max),
    }


async def fetch_body_temp(account: str, uid: str, user_type: str = "LLMREPORT") -> dict:
    """
    CMD: Temp — 수면 중 체온 상승 (°C 델타값, 절대 체온 아님).
    relay는 Min/Max만 제공하므로 avg = (Min + Max) / 2 로 계산한다.

    반환:
      {"body_temp_min": 0.2, "body_temp_max": 1.1, "body_temp_avg": 0.65}
    """
    raw = await _fetch_raw(account, uid, "Temp", user_type=user_type)
    t_min = float(raw.get("Min", 0.0))
    t_max = float(raw.get("Max", 0.0))
    return {
        "body_temp_min": t_min,
        "body_temp_max": t_max,
        "body_temp_avg": _calc_avg_float(t_min, t_max),
    }


async def fetch_environment(account: str, uid: str, user_type: str = "LLMREPORT") -> dict:
    """
    CMD: IndoorTemp + dB — 실내 온도·소음 집계.
    두 CMD를 병렬 호출해 결합한다.
    relay는 Min/Max만 제공하므로 avg = (Min + Max) / 2 로 계산한다.

    반환:
      {"temp_avg": 23.0, "temp_max": 25.0, "temp_min": 21.0,
       "db_avg": 40, "db_max": 58}
    """
    import asyncio
    temp_raw, db_raw = await asyncio.gather(
        _fetch_raw(account, uid, "IndoorTemp", user_type=user_type),
        _fetch_raw(account, uid, "dB", user_type=user_type),
    )
    t_min = float(temp_raw.get("Min", 0.0))
    t_max = float(temp_raw.get("Max", 0.0))
    d_max = int(db_raw.get("Max", 0))   # dB는 Max만 제공됨 (Min 없음)
    return {
        "temp_min": t_min,
        "temp_max": t_max,
        "temp_avg": _calc_avg_float(t_min, t_max, ndigits=1),
        "db_max":   d_max,
        "db_avg":   d_max,
    }


async def fetch_events(account: str, uid: str, user_type: str = "LLMREPORT") -> dict:
    """
    울음 감지·카메라 이탈 횟수.

    반환:
      {"cry_count": 2, "leave_count": 1}
    """
    raw = await _fetch_raw(account, uid, "Events", user_type=user_type)
    return {
        "cry_count":   int(raw.get("cry_count") or raw.get("CryCount") or 0),
        "leave_count": int(raw.get("leave_count") or raw.get("LeaveCount") or 0),
    }


def _parse_wakeup_count(day_wakeup: str) -> Optional[int]:
    """'5 times' 형태 문자열에서 정수를 추출한다. 파싱 불가 시 None 반환."""
    m = re.search(r"\d+", day_wakeup or "")
    return int(m.group()) if m else None


def _classify_sessions(sessions: list) -> list:
    """
    수면 세션 목록에 낮잠 여부(is_nap)를 추가한다.
    start 시각이 21:00 이전이면 낮잠, 이후면 밤잠으로 분류.
    """
    result = []
    for s in sessions:
        start_h = int(s.get("start", "0:0").split(":")[0])
        result.append({
            "start":        s.get("start", ""),
            "end":          s.get("end", ""),
            "duration_min": int(s.get("duration_min", 0)),
            "wake_up":      int(s.get("wake_up", 0)),
            "is_nap":       start_h < 21,
        })
    return result


def parse_sensor_data_day(raw: dict, target_date: date_cls) -> dict:
    """
    CMD=SensorData (ALL) 응답 하루치를 필드별로 파싱한다.

    SensorData 응답 구조:
      raw["SleepData"]  = {"day_gs": "7h19m", "day_pr": "0h59m",
                           "week_gs": "10h48m", "week_pr": "1h53m",
                           "month_gs": "10h11m", "month_pr": "1h47m",
                           "day_wakeup": "5 times", "status": "NORMAL",
                           "sessions": [...]}
      raw["Breath"]     = {"Min": 9, "Max": 16}
      raw["Temp"]       = {"Min": -2.2, "Max": 0.4}   ← 델타값
      raw["IndoorTemp"] = {"Min": 18.1, "Max": 22.5}
      raw["dB"]         = {"Max": 51}                  ← Min 없음
      raw["Humidity"]   = {"Min": 38, "Max": 47}
      raw["Bright"]     = {"Min": 24, "Max": 108}
      raw["birth_date"] = "2026-05-08"
    """
    sd   = raw.get("SleepData", {})
    b    = raw.get("Breath", {})
    t    = raw.get("Temp", {})
    it   = raw.get("IndoorTemp", {})
    db   = raw.get("dB", {})
    hum  = raw.get("Humidity", {})
    brt  = raw.get("Bright", {})

    b_min   = int(b.get("Min", 0))
    b_max   = int(b.get("Max", 0))
    t_min   = float(t.get("Min", 0.0))
    t_max   = float(t.get("Max", 0.0))
    it_min  = float(it.get("Min", 0.0))
    it_max  = float(it.get("Max", 0.0))

    result = {
        "date":             str(target_date),
        "sleep_min":        parse_duration_str(sd.get("day_gs", "")),
        "restless_min":     parse_duration_str(sd.get("day_pr", "")),
        "baby_age_months":  _calc_age_months(raw.get("birth_date", "")),
        "breath_min":       b_min,
        "breath_max":       b_max,
        "breath_avg":       _calc_avg_int(b_min, b_max),
        "body_temp_min":    t_min,
        "body_temp_max":    t_max,
        "body_temp_avg":    _calc_avg_float(t_min, t_max),
        "temp_min":         it_min,
        "temp_max":         it_max,
        "db_max":           int(db.get("Max", 0)),
        "month_sleep_h":    round(parse_duration_str(sd.get("month_gs", "")) / 60, 2),
        "month_restless_h": round(parse_duration_str(sd.get("month_pr", "")) / 60, 2),
        "week_sleep_h":     round(parse_duration_str(sd.get("week_gs", "")) / 60, 2) if sd.get("week_gs") else None,
        "week_restless_h":  round(parse_duration_str(sd.get("week_pr", "")) / 60, 2) if sd.get("week_pr") else None,
        "device_status":    sd.get("status"),
        "wakeup_count":     _parse_wakeup_count(sd.get("day_wakeup", "")),
        "sessions":         _classify_sessions(sd.get("sessions", [])) or None,
    }

    # 습도 (있을 때만)
    if hum:
        h_min = float(hum.get("Min", 0.0))
        h_max = float(hum.get("Max", 0.0))
        result["humidity_min"] = h_min
        result["humidity_max"] = h_max
        result["humidity_avg"] = _calc_avg_float(h_min, h_max, 1)

    # 조도 (있을 때만)
    if brt:
        br_min = float(brt.get("Min", 0.0))
        br_max = float(brt.get("Max", 0.0))
        result["bright_min"] = br_min
        result["bright_max"] = br_max
        result["bright_avg"] = _calc_avg_float(br_min, br_max, 1)

    return result


async def build_generate_request_from_sensor(
    account: str,
    uid: str,
    ref_date: date_cls,
    ser_no: str,
    user_type: str = "LLMREPORT",
) -> dict:
    """
    CMD=SensorData로 7일치를 날짜별 병렬 호출해
    GenerateReportRequest(**result)로 바로 사용 가능한 dict를 반환한다.

    ref_date: 마지막 날(포함). 7일치를 ref_date-6 ~ ref_date 순으로 수집.
    Breath/Temp/IndoorTemp/dB는 7일 평균으로 집계.
    월간 데이터는 마지막 날 응답에서 추출.
    Events는 미지원이므로 0 처리.
    """
    import asyncio
    from datetime import timedelta

    dates = [ref_date - timedelta(days=i) for i in range(6, -1, -1)]

    raws = await asyncio.gather(*[
        _fetch_raw(account, uid, "SensorData", date_str=str(d), user_type=user_type)
        for d in dates
    ])

    days = [parse_sensor_data_day(raw, d) for raw, d in zip(raws, dates)]

    # 7일치 수치 집계
    def _avg_int(key: str) -> int:
        return round(sum(d[key] for d in days) / 7)

    def _avg_float(key: str, ndigits: int = 2) -> float:
        return round(sum(d[key] for d in days) / 7, ndigits)

    b_min  = _avg_int("breath_min")
    b_max  = _avg_int("breath_max")
    t_min  = _avg_float("body_temp_min")
    t_max  = _avg_float("body_temp_max")
    it_min = _avg_float("temp_min", 1)
    it_max = _avg_float("temp_max", 1)
    db_max = max(d["db_max"] for d in days)

    last = days[-1]

    # 습도·조도: 제공된 날짜만 평균 (센서 없는 기기 대응)
    hum_days  = [d for d in days if d.get("humidity_avg") is not None]
    brt_days  = [d for d in days if d.get("bright_avg") is not None]

    env: dict = {
        "temp_min": it_min,
        "temp_max": it_max,
        "temp_avg": _calc_avg_float(it_min, it_max, 1),
        "db_max":   db_max,
        "db_avg":   db_max,
    }
    if hum_days:
        h_min_avg = round(sum(d["humidity_min"] for d in hum_days) / len(hum_days), 1)
        h_max_avg = round(sum(d["humidity_max"] for d in hum_days) / len(hum_days), 1)
        env["humidity_min"] = h_min_avg
        env["humidity_max"] = h_max_avg
        env["humidity_avg"] = round((h_min_avg + h_max_avg) / 2, 1)
    if brt_days:
        br_min_avg = round(sum(d["bright_min"] for d in brt_days) / len(brt_days), 1)
        br_max_avg = round(sum(d["bright_max"] for d in brt_days) / len(brt_days), 1)
        env["bright_min"] = br_min_avg
        env["bright_max"] = br_max_avg
        env["bright_avg"] = round((br_min_avg + br_max_avg) / 2, 1)

    sleep_list = []
    for d in days:
        entry: dict = {
            "date":         d["date"],
            "sleep_min":    d["sleep_min"],
            "restless_min": d["restless_min"],
        }
        if d.get("wakeup_count") is not None:
            entry["wakeup_count"] = d["wakeup_count"]
        if d.get("device_status"):
            entry["device_status"] = d["device_status"]
        if d.get("sessions"):
            entry["sessions"] = d["sessions"]
        sleep_list.append(entry)

    monthly: dict = {
        "month_sleep_h":    last["month_sleep_h"],
        "month_restless_h": last["month_restless_h"],
    }
    if last.get("week_sleep_h") is not None:
        monthly["week_sleep_h"]    = last["week_sleep_h"]
        monthly["week_restless_h"] = last.get("week_restless_h")

    return {
        "ser_no":          ser_no,
        "baby_age_months": last["baby_age_months"],
        "week_start":      str(dates[0]),
        "user_type":       "baby" if user_type == "LLMREPORT" else "senior",
        "sleep":           sleep_list,
        "breath": {
            "breath_min": b_min,
            "breath_max": b_max,
            "breath_avg": _calc_avg_int(b_min, b_max),
        },
        "body_temp": {
            "body_temp_min": t_min,
            "body_temp_max": t_max,
            "body_temp_avg": _calc_avg_float(t_min, t_max),
        },
        "environment": env,
        "monthly":     monthly,
        "events":      {"cry_count": 0, "leave_count": 0},
    }
