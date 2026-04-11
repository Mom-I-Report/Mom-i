from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime


class DailySleepLogIn(BaseModel):
    day_gs: str           # "9h30m"
    day_pr: str           # "18m"
    measured_date: date


class EnvironmentLogIn(BaseModel):
    temp_avg: float
    temp_max: float
    temp_min: float
    db_max: int
    measured_date: date


class EventLogIn(BaseModel):
    event_type: str       # "Crying" | "Leave"
    event_time: datetime


class SleepDataRequest(BaseModel):
    """맘아이 앱 → 우리 서버로 전송하는 일일 데이터"""
    ser_no: str
    sleep: DailySleepLogIn
    environment: EnvironmentLogIn
    events: List[EventLogIn] = []


class SleepDataResponse(BaseModel):
    status: str
    message: str
