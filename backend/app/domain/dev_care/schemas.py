"""
dev_care/schemas.py — 발달 케어 콘텐츠 Pydantic 스키마
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class DevelopmentalCareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     int
    type:                   str
    age_months:             int
    age_weeks:              Optional[int]
    age_label:              str
    wonder_weeks_leap:      Optional[int]
    is_sleep_regression:    bool
    dev_status:             str
    sleep_activities:       List[str]
    vaccination:            str
    separation_sleep_guide: str
