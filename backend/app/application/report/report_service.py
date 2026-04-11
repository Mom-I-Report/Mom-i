from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta

from app.infrastructure.database.repository import sleep_data_repo, report_repo
from app.infrastructure.llm.gemini_client import generate_insight


DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def _parse_hours(time_str: str) -> float:
    """'9h30m' → 9.5, '45m' → 0.75"""
    hours, mins = 0.0, 0.0
    if "h" in time_str:
        parts = time_str.split("h")
        hours = float(parts[0])
        time_str = parts[1]
    if "m" in time_str:
        mins = float(time_str.replace("m", ""))
    return round(hours + mins / 60, 2)


def _parse_minutes(time_str: str) -> int:
    """'18m' → 18, '1h5m' → 65"""
    hours, mins = 0, 0
    if "h" in time_str:
        parts = time_str.split("h")
        hours = int(parts[0])
        time_str = parts[1]
    if "m" in time_str:
        mins = int(time_str.replace("m", ""))
    return hours * 60 + mins


def build_report_data(db: Session, user_id: int, week_start: date) -> dict:
    """
    DB에서 1주치 데이터를 조회·집계하여 리포트 템플릿용 dict를 반환합니다.
    """
    from app.domain.sleep_data.entity import User
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError(f"사용자를 찾을 수 없습니다: {user_id}")

    sleep_logs = sleep_data_repo.get_weekly_sleep_logs(db, user_id, week_start)
    env_logs   = sleep_data_repo.get_weekly_environment_logs(db, user_id, week_start)
    event_logs = sleep_data_repo.get_weekly_event_logs(db, user_id, week_start)

    # ── 수면 집계 ──
    sleep_hours_list = [_parse_hours(l.day_gs) for l in sleep_logs if l.day_gs]
    restless_min_list= [_parse_minutes(l.day_pr) for l in sleep_logs if l.day_pr]
    avg_sleep_h      = round(sum(sleep_hours_list) / len(sleep_hours_list), 1) if sleep_hours_list else 0
    avg_restless_min = round(sum(restless_min_list) / len(restless_min_list)) if restless_min_list else 0

    # ── 환경 집계 ──
    temp_avgs = [e.temp_avg for e in env_logs if e.temp_avg is not None]
    temp_maxs = [e.temp_max for e in env_logs if e.temp_max is not None]
    temp_mins = [e.temp_min for e in env_logs if e.temp_min is not None]
    db_maxs   = [e.db_max  for e in env_logs if e.db_max  is not None]
    temp_avg  = round(sum(temp_avgs) / len(temp_avgs), 1) if temp_avgs else 0
    temp_max  = max(temp_maxs) if temp_maxs else 0
    temp_min  = min(temp_mins) if temp_mins else 0
    db_max    = max(db_maxs)   if db_maxs   else 0

    # ── 이벤트 집계 ──
    cry_count  = sum(1 for e in event_logs if e.event_type == "Crying")
    leave_count= sum(1 for e in event_logs if e.event_type == "Leave")

    # ── 일별 바 차트 데이터 ──
    max_h = max(sleep_hours_list) if sleep_hours_list else 10
    daily_sleep = []
    log_by_date = {l.measured_date: l for l in sleep_logs}
    for i in range(7):
        d = week_start + timedelta(days=i)
        log = log_by_date.get(d)
        if log:
            sh = _parse_hours(log.day_gs)
            rm = _parse_minutes(log.day_pr)
            sleep_pct   = int(sh / max_h * 75)
            restless_pct= int(rm / 60 / max_h * 75)
        else:
            sh, rm, sleep_pct, restless_pct = 0, 0, 0, 0
        daily_sleep.append({
            "label": DAY_KO[i],
            "sleep_h": sh,
            "restless_min": rm,
            "sleep_pct": sleep_pct,
            "restless_pct": restless_pct,
        })

    # ── 월령 계산 ──
    baby_age_months = relativedelta(date.today(), user.baby_birth).months + \
                      relativedelta(date.today(), user.baby_birth).years * 12

    # ── 주차 레이블 ──
    week_num = (week_start.day - 1) // 7 + 1
    week_label = f"{week_start.year}년 {week_start.month}월 {week_num}주차"

    # ── AI 인사이트 ──
    daily_summary = " / ".join(
        f"{d['label']} {d['sleep_h']}h" for d in daily_sleep
    )
    ai_comment = generate_insight({
        "baby_name": user.baby_name,
        "baby_age_months": baby_age_months,
        "week_label": week_label,
        "avg_sleep_h": avg_sleep_h,
        "avg_restless_min": avg_restless_min,
        "temp_avg": temp_avg,
        "db_max": db_max,
        "cry_count": cry_count,
        "leave_count": leave_count,
        "daily_summary": daily_summary,
    })

    # ── 이벤트 칩 ──
    events = []
    if cry_count:
        events.append({"label": f"울음 {cry_count}회", "style": ""})
    if leave_count:
        events.append({"label": f"카메라 이탈 {leave_count}회", "style": ""})
    if not events:
        events.append({"label": "특이 이벤트 없음", "style": "calm"})

    report_dict = {
        "baby_name":       user.baby_name,
        "week_label":      week_label,
        "created_at":      date.today().strftime("%Y-%m-%d"),
        "ser_no":          user.ser_no,
        "avg_sleep_h":     avg_sleep_h,
        "avg_restless_min":avg_restless_min,
        "cry_count":       cry_count,
        "leave_count":     leave_count,
        "temp_avg":        temp_avg,
        "temp_max":        temp_max,
        "temp_min":        temp_min,
        "db_max":          db_max,
        "ai_comment":      ai_comment,
        "daily_sleep":     daily_sleep,
        "events":          events,
    }

    # ── 리포트 이력 저장 ──
    report_repo.save_report(
        db=db,
        user_id=user_id,
        ai_kick_comment=ai_comment,
        measured_week_start=week_start,
    )

    return report_dict
