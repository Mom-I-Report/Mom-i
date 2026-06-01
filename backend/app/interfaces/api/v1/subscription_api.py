"""
subscription_api.py — 구독 관리 API (맘아이 서버 전용)

엔드포인트:
  POST   /api/v1/subscriptions          — 구독 등록 (X-API-Key)
  DELETE /api/v1/subscriptions/{ser_no} — 구독 해제 (X-API-Key)
  GET    /api/v1/subscriptions          — 구독 목록 조회 (X-API-Key, 관리용)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal, List, Optional
from datetime import datetime

from app.infrastructure.database.session import get_db
from app.core.security import verify_api_key
from app.infrastructure.database.repository import subscription_repo

router = APIRouter()


class SubscriptionCreate(BaseModel):
    ser_no:    str
    account:   str
    user_type: Literal["LLMREPORT", "LLMREPORTS"] = "LLMREPORT"


class SubscriptionResponse(BaseModel):
    ser_no:     str
    account:    str
    user_type:  str
    is_active:  bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="구독 등록",
    dependencies=[Depends(verify_api_key)],
)
def create_subscription(body: SubscriptionCreate, db: Session = Depends(get_db)):
    """
    맘아이 서버가 구독 유저를 리포트 서버에 등록합니다.
    이미 등록된 ser_no면 account·user_type을 갱신하고 is_active=True로 복구합니다.
    """
    return subscription_repo.create_subscription(db, body.ser_no, body.account, body.user_type)


@router.delete(
    "/{ser_no}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="구독 해제",
    dependencies=[Depends(verify_api_key)],
)
def deactivate_subscription(ser_no: str, db: Session = Depends(get_db)):
    """구독을 비활성화합니다. 데이터는 보존되고 스케줄러에서 제외됩니다."""
    if not subscription_repo.deactivate_subscription(db, ser_no):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="구독 정보를 찾을 수 없습니다")


@router.get(
    "",
    response_model=List[SubscriptionResponse],
    summary="구독 목록 조회",
    dependencies=[Depends(verify_api_key)],
)
def list_subscriptions(db: Session = Depends(get_db)):
    return subscription_repo.get_active_subscriptions(db)
