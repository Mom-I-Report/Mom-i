"""
dev_care_api.py — 발달 케어 콘텐츠 조회 API

엔드포인트:
  GET /api/v1/dev-care?age_months=8        — 월령으로 조회 (13개월 이상)
  GET /api/v1/dev-care?age_weeks=32        — 주차로 조회 (4~12개월 정밀)

JWT 인증 불필요 — 공개 참조 데이터
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.infrastructure.database.session import get_db
from app.infrastructure.database.repository import dev_care_repo
from app.domain.dev_care.schemas import DevelopmentalCareResponse

router = APIRouter()


@router.get(
    "",
    response_model=DevelopmentalCareResponse,
    summary="발달 케어 콘텐츠 조회",
)
def get_dev_care(
    age_months: Optional[int] = Query(None, ge=4, le=36, description="월령 (4~36개월)"),
    age_weeks:  Optional[int] = Query(None, ge=16, le=52, description="주차 (16~52주)"),
    db: Session = Depends(get_db),
):
    if age_weeks is not None:
        entry = dev_care_repo.get_by_age_weeks(db, age_weeks)
    elif age_months is not None:
        entry = dev_care_repo.get_by_age_months(db, age_months)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="age_months 또는 age_weeks 중 하나를 입력해주세요",
        )

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 월령의 발달 케어 콘텐츠가 없습니다",
        )

    return entry
