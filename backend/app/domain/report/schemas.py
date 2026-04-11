from pydantic import BaseModel
from typing import Optional
from datetime import date


class ReportResponse(BaseModel):
    report_id: int
    user_id: int
    baby_name: str
    week_label: str
    ai_kick_comment: str
    created_at: str


class ReportRequest(BaseModel):
    user_id: int
    week_start: Optional[date] = None   # None이면 최근 7일
