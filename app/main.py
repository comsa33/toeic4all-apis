import datetime
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.mongodb import close_mongodb_connection, connect_to_mongodb, mongodb
from app.db.redis_client import RedisClient, get_redis
from app.middleware.rate_limit import RateLimitMiddleware
from app.routes.api import part5_api, part6_api, part7_api
from app.routes.auth import auth_router
from app.utils.logger import setup_logging

# 로깅 설정
setup_logging(level=settings.log_level)
logger = logging.getLogger("toeic4all")


# 라이프스팬 컨텍스트 매니저
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 이벤트 처리 (startup)
    app.start_time = datetime.datetime.now(datetime.timezone.utc)
    logger.info("Starting application, connecting to MongoDB and Redis...")

    # MongoDB 연결
    await connect_to_mongodb()
    logger.info("MongoDB connection established")

    # Redis 연결
    await RedisClient.get_instance()
    logger.info("Redis connection established")

    yield  # 이 지점에서 애플리케이션이 실행됨

    # 종료 이벤트 처리 (shutdown)
    logger.info("Shutting down application, closing connections...")

    # Redis 연결 종료
    await RedisClient.close()
    logger.info("Redis connection closed")

    # MongoDB 연결 종료
    await close_mongodb_connection()
    logger.info("MongoDB connection closed")


# 프로덕션 환경에서 root_path 설정
root_path = "/api/v1/questions" if settings.environment == "production" else ""

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="TOEIC Question API",
    description="TOEIC 문제 조회 API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
    # OpenAPI URL을 절대 경로로 설정
    openapi_url=(
        "/api/v1/questions/openapi.json"
        if settings.environment == "production"
        else "/openapi.json"
    ),
    # root_path 설정으로 프록시 뒤에서도 올바른 URL 생성
    root_path=root_path,
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": "swagger",
    },
    openapi_tags=[
        {
            "name": "인증",
            "description": "인증 관련 엔드포인트. `/auth/token`에서 토큰을 얻은 후 오른쪽 상단의 '**Authorize**' 버튼을 클릭하여 인증할 수 있습니다.",
        },
        {
            "name": "Questions - Part 5",
            "description": "Part 5 문법/어휘 문제 조회 API. 인증이 필요합니다.",
        },
        {
            "name": "Questions - Part 6",
            "description": "Part 6 문법/어휘 문제 조회 API. 인증이 필요합니다.",
        },
        {
            "name": "Questions - Part 7",
            "description": "Part 7 문법/어휘 문제 조회 API. 인증이 필요합니다.",
        },
    ],
)

# security_schemes 설정
app.swagger_ui_oauth2_redirect_url = "/oauth2-redirect"

# 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 실제 프론트엔드 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 레이트 리미팅 미들웨어 추가
app.add_middleware(
    RateLimitMiddleware,
    max_requests=getattr(settings, "redis_rate_limit_max", 100),
    window_seconds=getattr(settings, "redis_rate_limit_window", 60),
)


# 글로벌 응답 미들웨어 - 모든 응답에 캐시 관련 헤더 추가
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)

    # API 응답에 기본 캐시 헤더 추가
    if "/api/v1/" in request.url.path:
        # GET 요청은 짧게 캐시 허용, 다른 요청은 캐시 금지
        if request.method == "GET":
            response.headers["Cache-Control"] = "public, max-age=60"  # 1분
        else:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

    return response


# 오류 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리기"""
    logger.error(f"Global exception handler: {exc}", exc_info=True)
    if settings.debug:
        # 디버그 모드에서는 상세 오류 정보 제공
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"서버 오류가 발생했습니다: {str(exc)}",
                "path": str(request.url),
            },
        )
    else:
        # 프로덕션 모드에서는 일반적인 오류 메시지만 제공
        return JSONResponse(
            status_code=500,
            content={"detail": "내부 서버 오류가 발생했습니다."},
        )


# 라우터 등록
app.include_router(
    part5_api.router,
    prefix="/part5",
    tags=["Questions - Part 5"],
)
app.include_router(
    part6_api.router,
    prefix="/part6",
    tags=["Questions - Part 6"],
)
app.include_router(
    part7_api.router,
    prefix="/part7",
    tags=["Questions - Part 7"],
)
app.include_router(
    auth_router,
    prefix="/swagger-auth",
    tags=["인증"],
)


# 시스템 모니터링 엔드포인트
@app.get("/system/health")
async def health_check(redis=Depends(get_redis)):
    """API 서버 상태 확인 엔드포인트"""
    # MongoDB 연결 확인
    db_status = "unknown"
    try:
        db_info = await mongodb.get_server_status()
        db_status = "online" if db_info.get("status") == "online" else "error"
    except Exception as e:
        logger.error(f"Health check - MongoDB error: {e}")
        db_status = "error"

    # Redis 연결 확인
    redis_status = "unknown"
    try:
        redis_ping = await redis.ping()
        redis_status = "online" if redis_ping else "error"
    except Exception as e:
        logger.error(f"Health check - Redis error: {e}")
        redis_status = "error"

    # 애플리케이션 업타임 계산
    uptime_seconds = None
    if hasattr(app, "start_time"):
        uptime_seconds = (
            datetime.datetime.now(datetime.timezone.utc) - app.start_time
        ).total_seconds()

    # 종합 상태
    overall_status = (
        "online" if db_status == "online" and redis_status == "online" else "degraded"
    )

    return {
        "status": overall_status,
        "message": "TOEIC Question API is running",
        "environment": settings.environment,
        "uptime_seconds": uptime_seconds,
        "version": app.version,
        "connections": {"mongodb": db_status, "redis": redis_status},
    }


# 캐시 통계 엔드포인트
@app.get("/system/cache-stats")
async def cache_stats(redis=Depends(get_redis)):
    """Redis 캐시 통계 정보 확인"""
    try:
        # Redis 정보
        info = await redis.info()

        # 각 캐시 키 수 계산
        part5_keys = len(await redis.keys("part5*"))
        part6_keys = len(await redis.keys("part6*"))
        part7_keys = len(await redis.keys("part7*"))
        metadata_keys = len(await redis.keys("metadata*"))
        token_keys = len(await redis.keys("token*"))
        lock_keys = len(await redis.keys("lock*"))

        # 서버 메모리 사용량
        memory_used = info.get("used_memory_human", "unknown")
        total_keys = info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)
        hit_rate = 0
        if total_keys > 0:
            hit_rate = (info.get("keyspace_hits", 0) / total_keys) * 100

        return {
            "total_keys": sum(
                [
                    part5_keys,
                    part6_keys,
                    part7_keys,
                    metadata_keys,
                    token_keys,
                    lock_keys,
                ]
            ),
            "memory_used": memory_used,
            "hit_rate_percent": round(hit_rate, 2),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "categories": {
                "part5": part5_keys,
                "part6": part6_keys,
                "part7": part7_keys,
                "metadata": metadata_keys,
                "token": token_keys,
                "lock": lock_keys,
            },
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {"status": "error", "message": str(e)}


# 캐시 정리 엔드포인트 (관리자 전용)
@app.post("/admin/system/clear-cache")
async def clear_cache(category: str = None, redis=Depends(get_redis)):
    """
    캐시 데이터 정리

    - **category**: 정리할 캐시 카테고리 (part5, part6, part7, metadata, token, lock, all)
    """
    try:
        cleared = 0
        if category == "all" or category is None:
            # 모든 캐시 정리
            cleared = len(await redis.keys("*"))
            await redis.flushdb()
        elif category in ["part5", "part6", "part7", "metadata", "token", "lock"]:
            # 특정 카테고리만 정리
            keys = await redis.keys(f"{category}*")
            if keys:
                cleared = len(keys)
                for key in keys:
                    await redis.delete(key)
        else:
            return {"status": "error", "message": "Invalid category"}

        return {
            "status": "success",
            "message": "Cache cleared successfully",
            "cleared_keys": cleared,
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return {"status": "error", "message": str(e)}


# 메인 엔드포인트
@app.get("/")
async def root():
    """API 서버 상태 확인 엔드포인트"""
    docs_url = (
        "/api/v1/questions/docs" if settings.environment == "production" else "/docs"
    )
    redoc_url = (
        "/api/v1/questions/redoc" if settings.environment == "production" else "/redoc"
    )

    return {
        "status": "online",
        "message": "TOEIC Question API is running",
        "docs": docs_url,
        "redoc": redoc_url,
    }
