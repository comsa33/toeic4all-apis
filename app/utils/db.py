import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from pymongo import AsyncMongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.config import settings
from app.utils.logger import logger


class MongoDBConfig(BaseSettings):
    """MongoDB 연결 설정 모델"""

    uri: str = Field(default_factory=lambda: settings.MONGODB_URI)
    database: str = Field(default_factory=lambda: settings.database_name)
    max_pool_size: int = 100
    min_pool_size: int = 10
    max_idle_time_ms: int = 60000
    socket_timeout_ms: int = 300000
    connect_timeout_ms: int = 60000
    server_selection_timeout_ms: int = 60000
    retry_writes: bool = True
    wait_queue_timeout_ms: int = 60000
    wait_queue_size: int = 1000

    @field_validator("uri")
    def validate_uri(cls, v):
        if not v.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError(
                "MongoDB URI must start with 'mongodb://' or 'mongodb+srv://'"
            )
        return v

    @model_validator(mode="after")
    def validate_config(self):
        if self.max_pool_size <= self.min_pool_size:
            raise ValueError("max_pool_size must be greater than min_pool_size")
        return self


class AsyncMongoDBClient:
    """싱글턴 MongoDB AsyncClient 클래스"""

    _instance = None
    _lock = asyncio.Lock()
    _client: Optional[AsyncMongoClient] = None
    _db: Optional[Database] = None
    _collections: Dict[str, Collection] = {}
    _health_check_task = None
    _config: MongoDBConfig = None
    _initialized = False  # 초기화 여부 클래스 변수로 선언

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AsyncMongoDBClient, cls).__new__(cls)
            # 여기서 initialized 속성은 인스턴스 생성시 자동으로 False로 설정
        return cls._instance

    async def initialize(self, config: Optional[MongoDBConfig] = None):
        """클라이언트 초기화 (필요시만 호출)"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:  # 이중 체크 락
                return

            self._config = config or MongoDBConfig()

            # 연결 옵션 구성
            mongo_options = {
                "maxPoolSize": self._config.max_pool_size,
                "minPoolSize": self._config.min_pool_size,
                "maxIdleTimeMS": self._config.max_idle_time_ms,
                "socketTimeoutMS": self._config.socket_timeout_ms,
                "connectTimeoutMS": self._config.connect_timeout_ms,
                "serverSelectionTimeoutMS": self._config.server_selection_timeout_ms,
                "retryWrites": self._config.retry_writes,
                "waitQueueTimeoutMS": self._config.wait_queue_timeout_ms,
            }

            try:
                # 비동기 클라이언트 생성
                # PyMongo 4.0부터는 비동기 작업을 위해 asyncio=True 옵션만 추가
                self._client = AsyncMongoClient(
                    self._config.uri,
                    **mongo_options,
                )

                self._db = self._client[self._config.database]

                # 주요 컬렉션 미리 참조
                self._collections = {
                    "part5_questions": self._db["part5_questions"],
                    "part6_sets": self._db["part6_sets"],
                    "part7_sets": self._db["part7_sets"],
                }

                # 연결 테스트
                await self._db.command("ping")
                logger.info(
                    f"MongoDB connection established to {self._config.database}"
                )

                # 주기적 헬스체크 시작
                self._start_health_check()

                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize MongoDB connection: {e}")
                raise

    def _start_health_check(self):
        """주기적 헬스체크 태스크 시작"""

        async def health_check_task():
            while True:
                try:
                    await asyncio.sleep(60)  # 60초마다 체크
                    if self._client:
                        await self._db.command("ping")
                        # logger.debug("MongoDB health check: OK")
                except Exception as e:
                    logger.error(f"MongoDB health check failed: {e}")
                    try:
                        # 문제가 있으면 재연결 시도
                        await self.initialize(self._config)
                    except Exception as e2:
                        logger.error(f"MongoDB reconnection failed: {e2}")

        # 이전 태스크가 있으면 취소
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()

        # 새 태스크 시작
        self._health_check_task = asyncio.create_task(health_check_task())

    @asynccontextmanager
    async def get_collection(self, collection_name: str):
        """컬렉션 컨텍스트 매니저"""
        if not self._initialized:
            await self.initialize()

        # 미리 캐시된 컬렉션이 있는지 확인
        if collection_name in self._collections:
            collection = self._collections[collection_name]
        else:
            collection = self._db[collection_name]
            # 자주 사용되는 컬렉션이면 캐시
            if collection_name.startswith(("part5_", "part6_", "part7_")):
                self._collections[collection_name] = collection

        try:
            yield collection
        except Exception as e:
            logger.error(f"Error in collection operation for {collection_name}: {e}")
            raise

    @property
    def client(self):
        """MongoDB 클라이언트 인스턴스 반환"""
        if not self._initialized:
            raise RuntimeError(
                "MongoDB client not initialized. Call initialize() first."
            )
        return self._client

    @property
    def db(self):
        """현재 데이터베이스 인스턴스 반환"""
        if not self._initialized:
            raise RuntimeError(
                "MongoDB client not initialized. Call initialize() first."
            )
        return self._db

    async def get_server_status(self) -> Dict[str, Any]:
        """서버 상태 정보 반환"""
        if not self._initialized:
            await self.initialize()

        try:
            status = await self._db.command("serverStatus")
            return {
                "status": "online",
                "connections": status.get("connections", {}),
                "network": status.get("network", {}),
                "uptime": status.get("uptime", 0),
                "ok": status.get("ok", 0),
                "pool_stats": {
                    "max_pool_size": self._config.max_pool_size,
                    "min_pool_size": self._config.min_pool_size,
                    "current_checked_out": status.get("connections", {}).get(
                        "current", 0
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Failed to get server status: {e}")
            return {"status": "error", "message": str(e)}

    async def close(self):
        """클라이언트 연결 종료"""
        if self._health_check_task:
            self._health_check_task.cancel()

        if self._client:
            self._client.close()
            self._initialized = False
            logger.info("MongoDB connection closed")


# 싱글턴 인스턴스 생성
mongodb = AsyncMongoDBClient()


# 앱 시작/종료 이벤트 핸들러 (FastAPI의 startup/shutdown 이벤트에 연결)
async def connect_to_mongodb():
    """애플리케이션 시작시 MongoDB 연결"""
    await mongodb.initialize()


async def close_mongodb_connection():
    """애플리케이션 종료시 MongoDB 연결 종료"""
    await mongodb.close()


# 편의 함수
def get_collection(collection_name: str):
    """컬렉션 비동기 컨텍스트 매니저"""
    return mongodb.get_collection(collection_name)


# 레거시 호환성 유지 (기존 코드와의 호환성)
async def get_database():
    """데이터베이스 의존성 주입을 위한 함수"""
    if not mongodb._initialized:
        await mongodb.initialize()
    return mongodb.db


# 컬렉션 컨텍스트 매니저 함수 - 기존 코드와의 호환성
def part5_collection():
    return mongodb.get_collection("part5_questions")


def part6_collection():
    return mongodb.get_collection("part6_sets")


def part7_collection():
    return mongodb.get_collection("part7_sets")
