from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import date, timedelta

from app.infrastructure.database.session import get_db
from app.infrastructure.pdf.generator import generate_pdf
from app.application.report.report_service import build_report_data

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "infrastructure" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _get_week_start(week_start: date | None) -> date:
    """week_start가 없으면 이번 주 월요일 반환"""
    if week_start:
        return week_start
    today = date.today()
    return today - timedelta(days=today.weekday())


@router.get("/report/preview", response_class=HTMLResponse)
async def preview_report(request: Request):
    """샘플 데이터로 리포트 HTML 미리보기 (DB 연결 불필요)"""
    sample = {
        "baby_name": "민준",
        "week_label": "2025년 4월 2주차",
        "created_at": "2025-04-11",
        "ser_no": "MT-00123",
        "avg_sleep_h": 9.2,
        "avg_restless_min": 18,
        "cry_count": 3,
        "leave_count": 1,
        "temp_avg": 23.1,
        "temp_max": 24.5,
        "temp_min": 21.8,
        "db_max": 62,
        "ai_comment": (
            "이번 주 민준이는 하루 평균 9시간 이상의 안정된 수면을 유지했습니다. "
            "특히 수요일과 목요일에 뒤척임이 줄어든 점이 인상적이에요. "
            "울음 이벤트가 3회 기록되었으나 대부분 짧은 시간 내 진정되었습니다. "
            "수면 환경의 평균 온도는 23.1°C로 영유아 권장 범위에 잘 맞춰져 있습니다. "
            "다음 주에도 지금처럼 일정한 취침 루틴을 유지해 주세요!"
        ),
        "daily_sleep": [
            {"label": "월", "sleep_h": 9.5, "restless_min": 22, "sleep_pct": 75, "restless_pct": 17},
            {"label": "화", "sleep_h": 8.8, "restless_min": 20, "sleep_pct": 69, "restless_pct": 16},
            {"label": "수", "sleep_h": 9.3, "restless_min": 14, "sleep_pct": 73, "restless_pct": 11},
            {"label": "목", "sleep_h": 9.6, "restless_min": 12, "sleep_pct": 76, "restless_pct":  9},
            {"label": "금", "sleep_h": 8.9, "restless_min": 19, "sleep_pct": 70, "restless_pct": 15},
            {"label": "토", "sleep_h": 9.0, "restless_min": 21, "sleep_pct": 71, "restless_pct": 16},
            {"label": "일", "sleep_h": 9.7, "restless_min": 16, "sleep_pct": 76, "restless_pct": 13},
        ],
        "events": [
            {"label": "울음 3회", "style": ""},
            {"label": "카메라 이탈 1회", "style": ""},
            {"label": "수면 환경 양호", "style": "calm"},
        ],
    }
    return templates.TemplateResponse("report.html", {"request": request, **sample})


@router.get("/report/{user_id}", response_class=HTMLResponse)
def get_weekly_report(
    request: Request,
    user_id: int,
    week_start: date | None = None,
    db: Session = Depends(get_db),
):
    """실제 DB 데이터 기반 주간 리포트 HTML 반환"""
    try:
        data = build_report_data(db, user_id, _get_week_start(week_start))
        return templates.TemplateResponse("report.html", {"request": request, **data})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/report/{user_id}/pdf")
def get_weekly_report_pdf(
    user_id: int,
    week_start: date | None = None,
    db: Session = Depends(get_db),
):
    """실제 DB 데이터 기반 PDF 다운로드"""
    try:
        data = build_report_data(db, user_id, _get_week_start(week_start))
        pdf_bytes = generate_pdf(data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=report_{user_id}.pdf"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
