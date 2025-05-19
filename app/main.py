import datetime
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.api import part5_api, part6_api, part7_api
from app.utils.db import close_mongodb_connection, connect_to_mongodb, mongodb
from app.utils.logger import setup_logging

# 로깅 설정
setup_logging(level=settings.log_level)
logger = logging.getLogger("toeic4all")


# 라이프스팬 컨텍스트 매니저
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 이벤트 처리 (startup)
    app.start_time = datetime.datetime.now(datetime.timezone.utc)
    logger.info("Starting application, connecting to MongoDB...")
    await connect_to_mongodb()
    logger.info("MongoDB connection established")

    yield  # 이 지점에서 애플리케이션이 실행됨

    # 종료 이벤트 처리 (shutdown)
    logger.info("Shutting down application, closing MongoDB connection...")
    await close_mongodb_connection()
    logger.info("MongoDB connection closed")


# FastAPI 애플리케이션 생성 - lifespan 인자 추가
app = FastAPI(
    title="TOEIC Question API",
    description="TOEIC 문제 조회 API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    lifespan=lifespan,  # 라이프스팬 컨텍스트 매니저 지정
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 실제 프론트엔드 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 의존성 주입용 함수
async def get_app_state():
    """애플리케이션 상태 정보 반환"""
    return {
        "app_version": app.version,
        "environment": settings.environment,
        "started_at": getattr(app, "start_time", None),
    }

# 사용자용 API 라우터 등록
app.include_router(
    part5_api.router,
    prefix=f"{settings.api_prefix}/questions/part5",
    tags=["Questions - Part 5"],
)
app.include_router(
    part6_api.router,
    prefix=f"{settings.api_prefix}/questions/part6",
    tags=["Questions - Part 6"],
)
app.include_router(
    part7_api.router,
    prefix=f"{settings.api_prefix}/questions/part7",
    tags=["Questions - Part 7"],
)


# 모니터링 엔드포인트
@app.get(f"{settings.api_prefix}/admin/system/health")
async def health_check(app_state: dict = Depends(get_app_state)):
    """API 서버 상태 확인 엔드포인트"""
    return {
        "status": "online",
        "message": "TOEIC Question Generator & API is running",
        "environment": settings.environment,
        "uptime": (
            (
                datetime.datetime.now(datetime.timezone.utc) - app.start_time
            ).total_seconds()
            if hasattr(app, "start_time")
            else None
        ),
        "version": app.version,
    }


@app.get(f"{settings.api_prefix}/admin/system/db-status")
async def db_status():
    """데이터베이스 상태 확인 엔드포인트"""
    return await mongodb.get_server_status()


# 메인 엔드포인트
@app.get("/")
async def root():
    """API 서버 상태 확인 엔드포인트"""
    return {"status": "online", "message": "TOEIC Question Generator & API is running"}
