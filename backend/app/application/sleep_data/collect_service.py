from sqlalchemy.orm import Session
from app.domain.sleep_data.schemas import SleepDataRequest
from app.infrastructure.database.repository import sleep_data_repo


def collect_daily_data(db: Session, payload: SleepDataRequest) -> dict:
    """
    맘아이 앱에서 전송한 일일 데이터를 DB에 저장합니다.
    ser_no → user_id 변환 후 3개 테이블에 각각 저장합니다.
    """
    user = sleep_data_repo.get_user_by_ser_no(db, payload.ser_no)
    if not user:
        raise ValueError(f"등록되지 않은 기기입니다: {payload.ser_no}")

    sleep_data_repo.save_sleep_log(
        db=db,
        user_id=user.user_id,
        day_gs=payload.sleep.day_gs,
        day_pr=payload.sleep.day_pr,
        measured_date=payload.sleep.measured_date,
    )

    sleep_data_repo.save_environment_log(
        db=db,
        user_id=user.user_id,
        temp_avg=payload.environment.temp_avg,
        temp_max=payload.environment.temp_max,
        temp_min=payload.environment.temp_min,
        db_max=payload.environment.db_max,
        measured_date=payload.environment.measured_date,
    )

    for event in payload.events:
        sleep_data_repo.save_event_log(
            db=db,
            user_id=user.user_id,
            event_type=event.event_type,
            event_time=event.event_time,
        )

    return {"user_id": user.user_id, "baby_name": user.baby_name}
