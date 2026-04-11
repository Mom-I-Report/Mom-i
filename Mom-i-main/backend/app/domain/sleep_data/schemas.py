from pydantic import BaseModel

class SleepReportRequest(BaseModel):
    user_id: str
    camera_id: str
    
class SleepReportResponse(BaseModel):
    report_id: str
    summary_text: str
