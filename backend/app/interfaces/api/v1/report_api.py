from fastapi import APIRouter

router = APIRouter()

@router.get("/report/{user_id}")
async def get_weekly_report(user_id: str):
    return {"user_id": user_id, "message": "주간 리포팅 목업 응답입니다."}
