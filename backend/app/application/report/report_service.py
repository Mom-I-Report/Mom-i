"""
report_service.py — 리포트 생성 핵심 비즈니스 로직

흐름 요약:
  1. 원본 데이터(수면·환경·호흡·체온·월간) DB 저장
  2. 캐시 확인 — 동일 주차 리포트가 이미 있으면 Gemini 재호출 없이 즉시 반환
  3. 이전 2주치 데이터 1회 조회 (DB 쿼리 중복 방지)
  4. 집계: 주간 요약 / 일별 / 트렌드 / 호흡 분석 / 체온 분석
  5. Gemini AI 조언 생성 — async (재시도·섹션검증·토큰로깅 포함)
  6. 리포트 저장 후 응답 반환

설계 원칙:
  - 개인정보(이름·생년월일) 일절 사용 안 함 → ser_no 단일 식별
  - DB 쿼리는 generate_report() 내에서 1회 (prev_data) 로 통합,
    하위 함수에 파라미터로 전달해 중복 호출 방지
  - 호흡수·체온 판정은 미국 소아과학회(AAP) 기준 월령 범위 적용
  - generate_report() / get_reports_list() / get_report_detail() 모두 async
    (Gemini async 호출을 위해 필요; DB는 sync SQLAlchemy 유지)
"""
import json
import logging

from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional, List

from app.domain.report.schemas import (
    GenerateReportRequest,
    GenerateReportResponse,
    ReportSummary,
    DailySummary,
    TrendData,
    BreathSummary,
    BodyTempSummary,
    SleepGuide,
    AgeKick,
    ReportListItem,
    ReportListResponse,
    ReportDetailResponse,
)
from app.domain.report.entity import WeeklyData
from app.infrastructure.database.repository import report_repo
from app.infrastructure.llm.gemini_client import generate_insight

logger = logging.getLogger(__name__)

# 요일 한글 변환 (date.weekday() → 0=월 ~ 6=일)
_DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

# ── 월령별 정상 호흡수 범위 (AAP 기준, 수면 중 회/분) ─────────────────────────
# (월령 상한, 최소, 최대) 순서 — 월령이 낮은 것부터 순서대로 매칭
_BREATH_RANGES = [
    (3,  30, 55),   # 0~3개월
    (6,  25, 50),   # 3~6개월
    (12, 20, 40),   # 6~12개월
    (24, 20, 35),   # 12~24개월
    (999, 20, 30),  # 24개월 이상
]

# ── 체온 상태 판정 기준 (°C) ────────────────────────────────────────────────
_BODY_TEMP_NORMAL_MAX  = 37.4   # 이하: 정상
_BODY_TEMP_CAUTION_MAX = 37.9   # 이하: 미열 주의
# 38.0 이상: 발열 의심


# ── 내부 헬퍼 함수 ──────────────────────────────────────────────────────────

def _week_label(week_start: date) -> str:
    """
    week_start 날짜를 '2026년 4월 2주차' 형식 문자열로 변환.
    week_num = (day - 1) // 7 + 1  →  1일=1주, 8일=2주, 15일=3주, 22일=4주
    """
    week_num = (week_start.day - 1) // 7 + 1
    return f"{week_start.year}년 {week_start.month}월 {week_num}주차"


def _get_breath_range(baby_age_months: int) -> tuple[int, int, str]:
    """
    월령에 맞는 정상 호흡수 범위를 반환한다.

    반환: (최소, 최대, 설명 문자열)
    예)  (20, 40, "20~40회/분 (생후 6~12개월 기준)")
    """
    for max_month, b_min, b_max in _BREATH_RANGES:
        if baby_age_months <= max_month:
            label = f"{b_min}~{b_max}회/분 (생후 {max_month}개월 이하 기준)"
            return b_min, b_max, label
    # 방어 코드: 범위 밖이면 마지막 기준 사용
    b_min, b_max = 20, 30
    return b_min, b_max, f"{b_min}~{b_max}회/분"


def _get_body_temp_status(body_temp_max: float) -> str:
    """
    수면 중 최고 체온을 기준으로 상태를 판정한다.

    기준 (최고 체온 기준으로 판정):
      37.4°C 이하  → 정상
      37.5~37.9°C  → 미열 주의
      38.0°C 이상  → 발열 의심 (소아과 상담 권장)
    """
    if body_temp_max <= _BODY_TEMP_NORMAL_MAX:
        return "정상"
    elif body_temp_max <= _BODY_TEMP_CAUTION_MAX:
        return "미열 주의"
    else:
        return "발열 의심"


def _build_summary(req: GenerateReportRequest) -> ReportSummary:
    """
    7일치 수면 데이터를 집계해 주간 요약(ReportSummary)을 생성한다.

    계산:
      avg_sleep_h      = sum(sleep_min) / 7 / 60   (시간, 소수점 1자리)
      avg_restless_min = sum(restless_min) / 7      (분, 정수)
      month_sleep_h    = monthly.month_sleep_h      (맘아이 서버 집계값 그대로)
    """
    sleep_mins    = [s.sleep_min for s in req.sleep]
    restless_mins = [s.restless_min for s in req.sleep]
    return ReportSummary(
        avg_sleep_h=round(sum(sleep_mins) / len(sleep_mins) / 60, 1),
        avg_restless_min=round(sum(restless_mins) / len(restless_mins)),
        cry_count=req.events.cry_count,
        leave_count=req.events.leave_count,
        temp_avg=req.environment.temp_avg,
        db_max=req.environment.db_max,
        month_sleep_h=req.monthly.month_sleep_h,
        month_restless_h=req.monthly.month_restless_h,
    )


def _build_daily(req: GenerateReportRequest) -> List[DailySummary]:
    """
    7일치 SleepDay를 DailySummary 리스트로 변환한다.

    변환:
      sleep_h = round(sleep_min / 60, 1)  (분 → 시간, 소수점 1자리)
      day     = _DAY_KO[date.weekday()]   (0=월, 6=일)
    """
    return [
        DailySummary(
            date=s.date,
            day=_DAY_KO[s.date.weekday()],
            sleep_h=round(s.sleep_min / 60, 1),
            restless_min=s.restless_min,
        )
        for s in req.sleep
    ]


def _build_breath_summary(req: GenerateReportRequest) -> BreathSummary:
    """
    호흡수 데이터를 분석해 BreathSummary를 생성한다.

    is_normal 판정:
      breath_avg가 해당 월령의 정상 범위(AAP 기준) 내에 있으면 True.
      최소 또는 최대 단일 수치가 범위를 벗어나도 평균이 정상이면 is_normal=True.
      → 일시적 수치 편차와 지속적 이상을 구분하기 위해 평균 기준으로 판정.
    """
    b = req.breath
    b_min, b_max, normal_range = _get_breath_range(req.baby_age_months)
    is_normal = b_min <= b.breath_avg <= b_max
    return BreathSummary(
        breath_min=b.breath_min,
        breath_max=b.breath_max,
        breath_avg=b.breath_avg,
        is_normal=is_normal,
        normal_range=normal_range,
    )


def _build_body_temp_summary(req: GenerateReportRequest) -> BodyTempSummary:
    """
    체온 데이터를 분석해 BodyTempSummary를 생성한다.

    status 판정:
      수면 중 최고 체온(body_temp_max)을 기준으로 판정.
      최고 체온이 가장 임상적 위험 신호에 가깝기 때문.

    status 값:
      "정상"       : 37.4°C 이하
      "미열 주의"  : 37.5~37.9°C
      "발열 의심"  : 38.0°C 이상 → AI가 소아과 상담 권장 문구 출력
    """
    bt = req.body_temp
    return BodyTempSummary(
        body_temp_min=bt.body_temp_min,
        body_temp_max=bt.body_temp_max,
        body_temp_avg=bt.body_temp_avg,
        status=_get_body_temp_status(bt.body_temp_max),
    )


def _build_trend(
    prev_data: List[WeeklyData],
    summary: ReportSummary,
    req: GenerateReportRequest,
) -> Optional[TrendData]:
    """
    직전 1주치 WeeklyData가 있으면 지난주 대비 트렌드를 계산한다.

    파라미터:
      prev_data : get_recent_weekly_data(weeks=2) 결과를 generate_report()에서
                  1회 조회 후 전달 (DB 쿼리 중복 방지).
                  prev_data[0] = 직전 주, prev_data[1] = 2주 전.

    반환:
      TrendData  : 각 지표의 이번 주 - 지난 주 차이값
                   양수(+) = 이번 주 증가, 음수(-) = 이번 주 감소
      None       : 이전 데이터가 없는 경우 (첫 주차 등)
    """
    if not prev_data:
        return None

    prev = prev_data[0]  # 직전 주

    # 이전 주 수면 집계 (sleep_json은 [{sleep_min, restless_min, ...}, ...] 형태)
    prev_sleeps   = [s["sleep_min"]    for s in prev.sleep_json]
    prev_restless = [s["restless_min"] for s in prev.sleep_json]
    prev_avg_sleep_h  = round(sum(prev_sleeps)   / len(prev_sleeps)   / 60, 1)
    prev_avg_restless = round(sum(prev_restless) / len(prev_restless))
    prev_cry          = prev.event_json.get("cry_count", 0)

    # 이전 주 호흡수 집계
    prev_breath_avg = prev.breath_json.get("breath_avg", 0)

    # 이전 주 체온 집계
    prev_body_temp_avg = prev.body_temp_json.get("body_temp_avg", 0.0)

    return TrendData(
        sleep_vs_last_week=round(summary.avg_sleep_h - prev_avg_sleep_h, 1),
        restless_vs_last_week=summary.avg_restless_min - prev_avg_restless,
        cry_vs_last_week=summary.cry_count - prev_cry,
        breath_vs_last_week=req.breath.breath_avg - prev_breath_avg,
        body_temp_vs_last_week=round(req.body_temp.body_temp_avg - prev_body_temp_avg, 1),
    )


def _build_ai_context(
    req: GenerateReportRequest,
    summary: ReportSummary,
    breath_summary: BreathSummary,
    body_temp_summary: BodyTempSummary,
    prev_data: List[WeeklyData],
) -> dict:
    """
    Gemini에 넘길 컨텍스트 dict를 구성한다.

    구조:
      - baby_age_months : 월령 (프롬프트 내 기준값 비교용)
      - week_label      : "2026년 4월 2주차"
      - this_week       : 이번 주 전체 요약 (수면·환경·호흡·체온·월간)
      - daily           : 7일치 일별 수면 (패턴 분석용)
      - last_week       : 직전 주 요약 (있을 때만 포함)
      - two_weeks_ago   : 2주 전 요약 (있을 때만 포함)

    prev_data는 generate_report()에서 weeks=2로 1회 조회한 결과를 재사용.
    (DB 쿼리 중복 없음)
    """
    ctx: dict = {
        "baby_age_months": req.baby_age_months,
        "week_label": _week_label(req.week_start),
        "this_week": {
            # 수면
            "avg_sleep_h":      summary.avg_sleep_h,
            "avg_restless_min": summary.avg_restless_min,
            "month_sleep_h":    summary.month_sleep_h,
            "month_restless_h": summary.month_restless_h,
            # 이벤트
            "cry_count":        summary.cry_count,
            "leave_count":      summary.leave_count,
            # 실내 환경
            "temp_avg":         req.environment.temp_avg,
            "temp_max":         req.environment.temp_max,
            "temp_min":         req.environment.temp_min,
            "db_avg":           req.environment.db_avg,
            "db_max":           req.environment.db_max,
            # 호흡수
            "breath_avg":       breath_summary.breath_avg,
            "breath_min":       breath_summary.breath_min,
            "breath_max":       breath_summary.breath_max,
            "breath_is_normal": breath_summary.is_normal,
            "breath_normal_range": breath_summary.normal_range,
            # 체온
            "body_temp_avg":    body_temp_summary.body_temp_avg,
            "body_temp_max":    body_temp_summary.body_temp_max,
            "body_temp_status": body_temp_summary.status,
        },
        # 일별 수면: AI가 요일별 패턴 파악에 사용
        "daily": [
            {
                "day":          _DAY_KO[s.date.weekday()],
                "sleep_h":      round(s.sleep_min / 60, 1),
                "restless_min": s.restless_min,
            }
            for s in req.sleep
        ],
    }

    # 직전 주 데이터가 있으면 지난주 비교 블록 추가
    if len(prev_data) >= 1:
        p = prev_data[0]
        ps = [s["sleep_min"]    for s in p.sleep_json]
        pr = [s["restless_min"] for s in p.sleep_json]
        ctx["last_week"] = {
            "avg_sleep_h":      round(sum(ps) / len(ps) / 60, 1),
            "avg_restless_min": round(sum(pr) / len(pr)),
            "cry_count":        p.event_json.get("cry_count", 0),
            "breath_avg":       p.breath_json.get("breath_avg", 0),
            "body_temp_avg":    p.body_temp_json.get("body_temp_avg", 0.0),
            "body_temp_max":    p.body_temp_json.get("body_temp_max", 0.0),
        }

    # 2주 전 데이터가 있으면 추가 (장기 트렌드 분석용)
    if len(prev_data) >= 2:
        p2 = prev_data[1]
        ps2 = [s["sleep_min"]    for s in p2.sleep_json]
        pr2 = [s["restless_min"] for s in p2.sleep_json]
        ctx["two_weeks_ago"] = {
            "avg_sleep_h":      round(sum(ps2) / len(ps2) / 60, 1),
            "avg_restless_min": round(sum(pr2) / len(pr2)),
            "cry_count":        p2.event_json.get("cry_count", 0),
            "breath_avg":       p2.breath_json.get("breath_avg", 0),
            "body_temp_avg":    p2.body_temp_json.get("body_temp_avg", 0.0),
        }

    return ctx


# ── Public API ───────────────────────────────────────────────────────────────

async def generate_report(db: Session, req: GenerateReportRequest) -> GenerateReportResponse:
    """
    주간 리포트를 생성하고 DB에 저장한 뒤 반환한다. (async)

    Step 1 — 원본 저장
      맘아이 서버로부터 받은 raw 데이터를 Weekly_Data에 upsert.
      데이터가 재전송되어도 항상 최신 원본을 보존한다.

    Step 2 — 캐시 확인 (Gemini 비용 절감)
      동일 (ser_no, week_start) 리포트가 이미 Generated_Reports에 있으면
      Gemini 재호출 없이 캐시된 리포트를 즉시 반환한다.
      단, Weekly_Data는 Step 1에서 항상 upsert해 다음 주 AI 트렌드 컨텍스트를 최신으로 유지.

    Step 3 — 이전 데이터 조회 (1회)
      get_recent_weekly_data(weeks=2)로 직전 2주치를 한 번만 조회.
      _build_trend()와 _build_ai_context() 모두 이 결과를 재사용 (쿼리 중복 없음).

    Step 4 — 집계
      _build_summary()          : 주간 평균 수면·뒤척임·이벤트·환경·월간
      _build_daily()            : 7일치 일별 DailySummary
      _build_breath_summary()   : 호흡수 + 월령 기준 정상 여부 판정
      _build_body_temp_summary(): 체온 + 상태 판정 (정상/미열주의/발열의심)
      _build_trend()            : 직전 주 대비 5개 지표 변화량

    Step 5 — AI 조언 생성 (async)
      _build_ai_context()로 최대 3주치 컨텍스트 dict 구성.
      await generate_insight()로 Gemini 비동기 호출
        → 재시도(최대 3회) + 3필드 검증(ai_comment/sleep_guide/age_kick) + 토큰 로깅 포함.

    Step 6 — 리포트 저장
      Generated_Reports에 upsert 후 GenerateReportResponse 반환.
    """
    # Step 1 — 원본 데이터 저장 (항상 실행)
    report_repo.save_weekly_data(
        db=db,
        ser_no=req.ser_no,
        week_start=req.week_start,
        sleep_json=[s.model_dump(mode="json") for s in req.sleep],
        env_json=req.environment.model_dump(),
        event_json=req.events.model_dump(),
        breath_json=req.breath.model_dump(),
        body_temp_json=req.body_temp.model_dump(),
        monthly_json=req.monthly.model_dump(),
    )

    # Step 2 — 캐시 확인
    cached = report_repo.get_existing_report(db, req.ser_no, req.week_start)
    if cached:
        logger.info(
            "[리포트 캐시 히트] ser_no=%s week_start=%s — Gemini 재호출 생략",
            req.ser_no, req.week_start,
        )
        return GenerateReportResponse.model_validate(cached.report_json)

    # Step 3 — 이전 2주치 조회 (1회, 이후 재사용)
    prev_data = report_repo.get_recent_weekly_data(
        db, req.ser_no, req.week_start, weeks=2
    )

    # Step 4 — 집계
    summary           = _build_summary(req)
    daily             = _build_daily(req)
    breath_summary    = _build_breath_summary(req)
    body_temp_summary = _build_body_temp_summary(req)
    trend             = _build_trend(prev_data, summary, req)

    # Step 5 — AI 조언 생성 (비동기, JSON dict 반환)
    ai_context  = _build_ai_context(req, summary, breath_summary, body_temp_summary, prev_data)
    ai_result   = await generate_insight(ai_context)
    ai_comment  = ai_result.get("ai_comment", [])
    sleep_guide = SleepGuide(**ai_result["sleep_guide"]) if "sleep_guide" in ai_result else None
    age_kick    = AgeKick(**ai_result["age_kick"]) if "age_kick" in ai_result else None

    # Step 6 — 응답 객체 생성 및 저장
    week_label  = _week_label(req.week_start)
    report_data = GenerateReportResponse(
        ser_no=req.ser_no,
        week_start=req.week_start,
        week_label=week_label,
        generated_at=datetime.now(),
        summary=summary,
        breath=breath_summary,
        body_temp=body_temp_summary,
        daily=daily,
        trend=trend,
        ai_comment=ai_comment,
        sleep_guide=sleep_guide,
        age_kick=age_kick,
    )

    report_repo.save_report(
        db=db,
        ser_no=req.ser_no,
        week_start=req.week_start,
        report_json=report_data.model_dump(mode="json"),
        ai_comment=json.dumps(ai_comment, ensure_ascii=False),
    )

    return report_data


async def get_reports_list(db: Session, ser_no: str) -> ReportListResponse:
    """
    GET /reports — 카드형 목록 조회. (async)
    최근 10건을 최신순으로 반환한다.
    """
    reports = report_repo.get_reports_list(db, ser_no, limit=10)
    if not reports:
        raise ValueError("조회 가능한 리포트가 없습니다.")

    items = []
    for r in reports:
        rj = r.report_json or {}
        summary = rj.get("summary", {})
        sg = rj.get("sleep_guide")
        items.append(ReportListItem(
            report_id=r.id,
            week_start=r.week_start,
            week_label=_week_label(r.week_start),
            avg_sleep_h=summary.get("avg_sleep_h", 0.0),
            avg_restless_min=summary.get("avg_restless_min", 0),
            sleep_guide_method=sg.get("method_name") if sg else None,
        ))
    return ReportListResponse(reports=items, total=len(items))


async def get_report_detail(db: Session, report_id: int, ser_no: str) -> ReportDetailResponse:
    """
    GET /reports/{report_id} — 상세 조회. (async)
    ser_no 격리 검증: 토큰의 ser_no와 리포트의 ser_no가 다르면 404 반환.
    """
    report = report_repo.get_report_by_id(db, report_id)
    if not report:
        raise ValueError("리포트를 찾을 수 없습니다.")
    if report.ser_no != ser_no:
        raise ValueError("리포트를 찾을 수 없습니다.")

    rj = dict(report.report_json)
    rj["report_id"] = report.id
    rj["ser_no"]    = report.ser_no
    return ReportDetailResponse.model_validate(rj)
