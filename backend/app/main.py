import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 엔티티를 먼저 import해야 create_tables()가 테이블을 인식한다
import app.domain.report.entity  # noqa

from app.interfaces.api.v1 import report_api, admin_api
from app.infrastructure.database.session import create_tables
from app.infrastructure.scheduler import start_scheduler
from app.infrastructure.emtake import client as emtake_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    start_scheduler()
    yield
    await emtake_client.close()


app = FastAPI(
    title="맘아이 리포트 서버",
    description="맘아이 앱 연동 영유아 주간 수면 AI 리포트 생성·보관·조회 서버",
    version="0.2.0",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 운영 시 실제 앱 도메인으로 교체
    allow_credentials=False,    # Bearer JWT 사용 — 쿠키 불필요. allow_origins=["*"]와 credentials=True 병용 불가
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 라우터 등록 ──
app.include_router(report_api.router, prefix="/api/v1/reports", tags=["리포트"])
app.include_router(admin_api.router,  prefix="/api/v1/admin",   tags=["관리자"])


@app.get("/", tags=["시스템"])
async def root():
    return {"message": "맘아이 리포트 서버"}


@app.get("/health", tags=["시스템"])
async def health():
    return {"status": "ok", "version": app.version}
