from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.interfaces.api.v1 import report_api, etf_api
from app.infrastructure.database.session import create_tables
from app.infrastructure.scheduler import start_scheduler

app = FastAPI(
    title="M-Take 리포트 서버",
    description="맘아이 앱 연동 영유아 주간 수면 AI 리포트 생성·보관·조회 서버",
    version="0.2.0",
)

# ── CORS ──
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

# ── 라우터 등록 ──
app.include_router(report_api.router, prefix="/api/v1/report", tags=["리포트"])
app.include_router(etf_api.router,    prefix="/api/v1/etf",    tags=["ETF 리밸런싱"])

@app.get("/")
async def root():
    return {"message": "M-Take 리포트 서버"}
