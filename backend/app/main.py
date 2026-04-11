from fastapi import FastAPI
from app.interfaces.api.v1 import report_api, sleep_data_api

app = FastAPI(
    title="M-Take Sleep Analysis API",
    description="카메라 기반 영유아 수면 분석 및 주간 리포트 시스템 API",
    version="0.1.0"
)

app.include_router(report_api.router, prefix="/api/v1", tags=["reports"])
app.include_router(sleep_data_api.router, prefix="/api/v1/sleep-data", tags=["sleep-data"])

@app.get("/")
async def root():
    return {"message": "Welcome to M-Take Sleep Analysis API"}
