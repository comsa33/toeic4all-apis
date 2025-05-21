from functools import lru_cache
from typing import Any, Dict

from app.config import Settings, settings
from app.db.mongodb import AsyncMongoDBClient, mongodb
from app.utils.logger import logger


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """설정 인스턴스 반환 (캐싱)"""
    return settings


async def get_mongodb() -> AsyncMongoDBClient:
    """MongoDB 클라이언트 인스턴스 의존성 주입"""
    if not mongodb._initialized:
        await mongodb.initialize()
    return mongodb


async def get_db_connection_stats() -> Dict[str, Any]:
    """MongoDB 연결 통계 정보 반환"""
    try:
        return await mongodb.get_server_status()
    except Exception as e:
        logger.error(f"Failed to get MongoDB connection stats: {e}")
        return {"status": "error", "message": str(e)}
