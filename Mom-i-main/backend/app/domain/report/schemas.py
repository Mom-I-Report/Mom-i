from pydantic import BaseModel
from typing import Optional

class ReportResponse(BaseModel):
    report_id: str
    user_id: str
    summary_insight: str
    pdf_url: Optional[str] = None
