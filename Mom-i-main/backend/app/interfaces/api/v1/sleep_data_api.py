from fastapi import APIRouter

router = APIRouter()

@router.post("/data")
async def collect_sleep_data(device_id: str):
    # 기기(카메라/센서) 인스턴스에서 전송되는 스트리밍 데이터/이벤트 수집
    return {"status": "success", "message": "데이터 수집 접수 완료"}
