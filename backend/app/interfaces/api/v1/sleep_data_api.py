from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.domain.sleep_data.schemas import SleepDataRequest, SleepDataResponse
from app.application.sleep_data.collect_service import collect_daily_data

router = APIRouter()


@router.post("/data", response_model=SleepDataResponse)
def receive_sleep_data(payload: SleepDataRequest, db: Session = Depends(get_db)):
    """맘아이 앱 → 일일 수면/환경/이벤트 데이터 수신 및 DB 저장"""
    try:
        result = collect_daily_data(db, payload)
        return SleepDataResponse(
            status="success",
            message=f"{result['baby_name']} 아기 데이터가 저장되었습니다.",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
