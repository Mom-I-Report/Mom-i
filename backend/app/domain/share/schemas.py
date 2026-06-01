"""
share/schemas.py — 공유 수신자 목록 Pydantic 스키마
"""
from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Literal
from datetime import datetime
import re


class ShareTargetCreate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    name: str
    contact: str
    type: Literal["sms", "email"]

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("이름을 입력해주세요")
        if len(v) > 50:
            raise ValueError("이름은 50자 이하여야 합니다")
        return v

    @field_validator("contact")
    @classmethod
    def contact_format(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("연락처를 입력해주세요")
        return v

    @field_validator("type")
    @classmethod
    def validate_type_contact(cls, v: str) -> str:
        return v


class ShareTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact: str
    type: str
    created_at: datetime


class ShareTargetListResponse(BaseModel):
    targets: List[ShareTargetResponse]
    total: int
