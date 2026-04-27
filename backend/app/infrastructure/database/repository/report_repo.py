"""
report_repo.py — Generated_Reports / Weekly_Data DB 접근 레이어

테이블 구조:
  - Weekly_Data       : 맘아이 서버로부터 받은 주간 원본 데이터 (AI 3주 트렌드용)
  - Generated_Reports : AI가 생성한 최종 리포트 (앱 재열람 + 조언 참고용)

모든 INSERT/UPDATE는 (ser_no + week_start) 기준 upsert 방식.
동일 주차 데이터가 재전송되면 덮어쓴다 (에러 없이 처리).
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date, timedelta
from typing import List, Optional

from app.domain.report.entity import WeeklyData, GeneratedReport


# ── Weekly_Data ──────────────────────────────────────────────────────────────

def save_weekly_data(
    db: Session,
    ser_no: str,
    week_start: date,
    sleep_json: list,
    env_json: dict,
    event_json: dict,
    breath_json: dict,
    body_temp_json: dict,
    monthly_json: dict,
) -> WeeklyData:
    """
    주간 원본 데이터를 Weekly_Data 테이블에 저장한다 (upsert).

    저장 목적:
      - AI 컨텍스트 구성 시 최대 3주치 이전 데이터를 조회해 트렌드를 분석하기 위함.
      - 리포트 생성 서버는 개인정보(이름·생년월일)를 저장하지 않으므로
        원본 데이터는 ser_no(기기 식별자) 기준으로만 관리한다.

    파라미터:
      sleep_json     : [{date, sleep_min, restless_min}, ...] — 7일치 수면 데이터
      env_json       : {temp_avg, temp_max, temp_min, db_max, db_avg} — 실내 환경
      event_json     : {cry_count, leave_count} — 이벤트 횟수
      breath_json    : {breath_min, breath_max, breath_avg} — 수면 중 호흡수(회/분)
      body_temp_json : {body_temp_min, body_temp_max, body_temp_avg} — 체온 상승(°C)
      monthly_json   : {month_sleep_h, month_restless_h} — 월간 평균 (장기 트렌드용)

    upsert 정책:
      UNIQUE KEY (ser_no, week_start) — 같은 주차 재전송 시 모든 필드 덮어쓰기.
    """
    existing = db.query(WeeklyData).filter(
        and_(WeeklyData.ser_no == ser_no, WeeklyData.week_start == week_start)
    ).first()

    if existing:
        # 동일 주차 재전송: 모든 컬럼 업데이트
        existing.sleep_json     = sleep_json
        existing.env_json       = env_json
        existing.event_json     = event_json
        existing.breath_json    = breath_json
        existing.body_temp_json = body_temp_json
        existing.monthly_json   = monthly_json
    else:
        existing = WeeklyData(
            ser_no=ser_no,
            week_start=week_start,
            sleep_json=sleep_json,
            env_json=env_json,
            event_json=event_json,
            breath_json=breath_json,
            body_temp_json=body_temp_json,
            monthly_json=monthly_json,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def get_recent_weekly_data(
    db: Session,
    ser_no: str,
    week_start: date,
    weeks: int = 2,
) -> List[WeeklyData]:
    """
    이전 N주치 WeeklyData를 최신순으로 조회한다.

    사용 목적:
      - report_service._build_trend()   : weeks=2 로 호출, [0]=직전주, [1]=2주전
      - report_service._build_ai_context(): 동일 prev_data 재사용 (쿼리 1회)

    조회 범위:
      cutoff = week_start - N주
      cutoff <= week_start < 이번 주 week_start  (이번 주 제외)

    반환:
      최신순 정렬 리스트 — prev_data[0]이 가장 최근 이전 주.
      데이터 없으면 빈 리스트 [] 반환 (예외 없음).
    """
    cutoff = week_start - timedelta(weeks=weeks)
    return (
        db.query(WeeklyData)
        .filter(
            and_(
                WeeklyData.ser_no == ser_no,
                WeeklyData.week_start >= cutoff,
                WeeklyData.week_start < week_start,
            )
        )
        .order_by(WeeklyData.week_start.desc())
        .all()
    )


# ── Generated_Reports ────────────────────────────────────────────────────────

def get_existing_report(
    db: Session,
    ser_no: str,
    week_start: date,
) -> GeneratedReport | None:
    """
    (ser_no, week_start) 기준으로 이미 생성된 리포트를 조회한다.

    사용 목적:
      report_service.generate_report() 에서 Gemini 호출 전 캐시 확인용.
      동일 주차 리포트가 이미 있으면 AI 재호출 없이 즉시 반환해 비용을 절감한다.

    반환:
      GeneratedReport 객체 (존재하면) / None (없으면)
    """
    return db.query(GeneratedReport).filter(
        and_(GeneratedReport.ser_no == ser_no, GeneratedReport.week_start == week_start)
    ).first()


def save_report(
    db: Session,
    ser_no: str,
    week_start: date,
    report_json: dict,
    ai_comment: str,
) -> GeneratedReport:
    """
    AI가 생성한 최종 리포트를 Generated_Reports 테이블에 저장한다 (upsert).

    저장 목적:
      - 앱에서 사용자가 이전 리포트를 재열람할 때 반환.
      - ai_comment를 별도 컬럼으로 분리 저장 → 향후 이전 조언 참고 기능에 활용.

    파라미터:
      report_json : GenerateReportResponse 전체 구조를 JSON으로 직렬화한 dict.
                    모든 리포트 필드(summary, breath, body_temp, daily, trend, ai_comment)가 포함됨.
      ai_comment  : AI 조언 텍스트 (report_json에도 포함되지만 빠른 접근을 위해 별도 저장).

    upsert 정책:
      UNIQUE KEY (ser_no, week_start) — 동일 주차 재전송 시 최신 내용으로 덮어쓰기.
    """
    existing = db.query(GeneratedReport).filter(
        and_(GeneratedReport.ser_no == ser_no, GeneratedReport.week_start == week_start)
    ).first()

    if existing:
        existing.report_json = report_json
        existing.ai_comment  = ai_comment
    else:
        existing = GeneratedReport(
            ser_no=ser_no,
            week_start=week_start,
            report_json=report_json,
            ai_comment=ai_comment,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def get_report_by_id(
    db: Session,
    report_id: int,
) -> Optional[GeneratedReport]:
    """primary key로 단건 리포트를 조회한다. 없으면 None 반환."""
    return db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()


def get_reports_list(
    db: Session,
    ser_no: str,
    limit: int = 10,
) -> List[GeneratedReport]:
    """
    ser_no 기준 최근 리포트 목록을 최신순으로 조회한다. (카드형 목록용)
    rolling 삭제 정책(3주)과 무관하게 현재 DB에 있는 데이터를 반환한다.
    """
    return (
        db.query(GeneratedReport)
        .filter(GeneratedReport.ser_no == ser_no)
        .order_by(GeneratedReport.week_start.desc())
        .limit(limit)
        .all()
    )


def get_admin_stats(db: Session) -> dict:
    """
    관리자 대시보드용 서버 통계를 반환한다.

    반환 항목:
      total_reports   : 전체 리포트 생성 건수
      active_devices  : 리포트가 존재하는 고유 기기(ser_no) 수
      today_reports   : 오늘 생성된 리포트 수 (created_at 기준)
      week_reports    : 이번 주(월요일 기준) 생성된 리포트 수
      last_generated_at : 가장 최근 리포트 생성 시각
      recent_reports  : 최근 생성된 리포트 10건 요약
    """
    today = date.today()
    week_monday = today - timedelta(days=today.weekday())

    total_reports  = db.query(func.count(GeneratedReport.id)).scalar() or 0
    active_devices = db.query(func.count(func.distinct(GeneratedReport.ser_no))).scalar() or 0
    today_reports  = db.query(func.count(GeneratedReport.id)).filter(
        func.date(GeneratedReport.created_at) == today
    ).scalar() or 0
    week_reports   = db.query(func.count(GeneratedReport.id)).filter(
        GeneratedReport.week_start >= week_monday
    ).scalar() or 0

    last = db.query(GeneratedReport).order_by(GeneratedReport.created_at.desc()).first()
    recent = db.query(GeneratedReport).order_by(GeneratedReport.created_at.desc()).limit(10).all()

    return {
        "total_reports": total_reports,
        "active_devices": active_devices,
        "today_reports": today_reports,
        "week_reports": week_reports,
        "last_generated_at": last.created_at.isoformat() if last and last.created_at else None,
        "recent_reports": [
            {
                "report_id": r.id,
                "ser_no": r.ser_no,
                "week_start": r.week_start.isoformat(),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent
        ],
    }


# ── 관리자 기기 조회 ──────────────────────────────────────────────────────────

def get_all_devices(db: Session) -> list[dict]:
    """모든 ser_no별 구독 시작일·마지막 리포트일·리포트 수를 반환한다."""
    rows = (
        db.query(
            GeneratedReport.ser_no,
            func.min(GeneratedReport.created_at).label("subscribed_at"),
            func.max(GeneratedReport.created_at).label("last_report_at"),
            func.count(GeneratedReport.id).label("report_count"),
        )
        .group_by(GeneratedReport.ser_no)
        .order_by(func.max(GeneratedReport.created_at).desc())
        .all()
    )
    return [
        {
            "ser_no":        r.ser_no,
            "subscribed_at": r.subscribed_at.isoformat() if r.subscribed_at else None,
            "last_report_at": r.last_report_at.isoformat() if r.last_report_at else None,
            "report_count":  r.report_count,
        }
        for r in rows
    ]


def get_device_reports(db: Session, ser_no: str, limit: int = 3) -> list[dict]:
    """특정 ser_no의 최근 N주치 리포트 전체를 반환한다."""
    reports = (
        db.query(GeneratedReport)
        .filter(GeneratedReport.ser_no == ser_no)
        .order_by(GeneratedReport.week_start.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "report_id":  r.id,
            "week_start": r.week_start.isoformat(),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "report_json": r.report_json,
        }
        for r in reports
    ]


# ── Rolling 삭제 ─────────────────────────────────────────────────────────────

def delete_old_data(db: Session) -> None:
    """
    보존 기간 초과 데이터를 물리 삭제한다.

    실행 주기: 매주 월요일 10:00 KST (scheduler.py에서 자동 호출).

    삭제 기준:
      - Generated_Reports : 5주 초과 (앱 3주 열람 + 여유 2주)
      - Weekly_Data       : 12주 초과 (AI 고도화 컨텍스트용, 아기 발달 주기 기준 3개월)

    소프트 삭제 없음 — 개인정보 최소화 원칙에 따라 완전 물리 삭제.
    """
    today = date.today()
    db.query(GeneratedReport).filter(
        GeneratedReport.week_start < today - timedelta(weeks=5)
    ).delete()
    db.query(WeeklyData).filter(
        WeeklyData.week_start < today - timedelta(weeks=12)
    ).delete()
    db.commit()
