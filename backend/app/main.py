from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.interfaces.api.v1 import report_api, sleep_data_api
from app.infrastructure.database.session import create_tables
from app.infrastructure.scheduler import start_scheduler

app = FastAPI(
    title="M-Take Sleep Analysis API",
    description="맘아이 앱 연동 영유아 수면 분석 및 주간 리포트 시스템",
    version="0.1.0",
)

# ── CORS (맘아이 앱 도메인 허용) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 운영 시 실제 앱 도메인으로 교체
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_tables()
    start_scheduler()

app.include_router(report_api.router,     prefix="/api/v1", tags=["리포트"])
app.include_router(sleep_data_api.router, prefix="/api/v1/sleep-data", tags=["수면 데이터"])

@app.get("/")
async def root():
    return {"message": "M-Take Sleep Analysis API"}
