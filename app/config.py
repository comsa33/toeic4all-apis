import os
import pathlib
from typing import Any, Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 환경 로드
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if ENVIRONMENT == "development":
    from dotenv import load_dotenv

    # 현재 파일의 디렉토리 경로 구하기
    BASE_DIR = pathlib.Path(__file__).parent
    # .env 파일 경로 설정
    ENV_PATH = BASE_DIR / ".env"
    # .env 파일 로드
    load_dotenv(ENV_PATH)


class MongoDBSettings(BaseSettings):
    """MongoDB 관련 설정"""

    MONGODB_URI: str = Field(
        default_factory=lambda: os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
        description="MongoDB 연결 URL",
    )
    database_name: str = Field(
        default_factory=lambda: os.getenv("DATABASE_NAME", "toeic4all"),
        description="MongoDB 데이터베이스 이름",
    )
    max_pool_size: int = Field(
        default_factory=lambda: int(os.getenv("MONGODB_MAX_POOL_SIZE", "50")),
        description="MongoDB 최대 연결 풀 크기",
    )
    min_pool_size: int = Field(
        default_factory=lambda: int(os.getenv("MONGODB_MIN_POOL_SIZE", "10")),
        description="MongoDB 최소 연결 풀 크기",
    )

    @field_validator("MONGODB_URI")
    def validate_MONGODB_URI(cls, v):
        if not v.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("MongoDB URL must start with mongodb:// or mongodb+srv://")
        return v

    @field_validator("max_pool_size")
    def validate_max_pool_size(cls, v):
        if not 10 <= v <= 100:
            raise ValueError("max_pool_size must be between 10 and 100")
        return v


class RedisSettings(BaseSettings):
    """Redis 관련 설정"""
    redis_url: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        description="Redis 연결 URL"
    )
    redis_ttl: int = Field(
        default_factory=lambda: int(os.getenv("REDIS_TTL", "3600")),
        description="Redis 키 기본 TTL (초)"
    )
    redis_rate_limit_max: int = Field(
        default_factory=lambda: int(os.getenv("REDIS_RATE_LIMIT_MAX", "100")),
        description="API 최대 요청 수 (기본 분당 100회)"
    )
    redis_rate_limit_window: int = Field(
        default_factory=lambda: int(os.getenv("REDIS_RATE_LIMIT_WINDOW", "60")),
        description="레이트 리밋 윈도우 (초)"
    )


class APISettings(BaseSettings):
    """API 관련 설정"""

    api_prefix: str = Field(
        default_factory=lambda: os.getenv("API_PREFIX", "/api/v1/questions"),
        description="API 경로 접두사",
    )


class AppSettings(BaseSettings):
    """애플리케이션 설정"""

    environment: str = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development"),
        description="실행 환경 (development, staging, production)",
    )
    debug: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true",
        description="디버그 모드 활성화 여부",
    )
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"),
        description="로깅 레벨",
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )


class AuthSettings(BaseSettings):
    """인증 관련 설정"""
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", ""),
        description="JWT 서명에 사용되는 비밀 키",
    )
    ALGORITHM: str = Field(
        default_factory=lambda: os.getenv("ALGORITHM", "HS256"),
        description="JWT 서명 알고리즘",
    )
    AUTH_SERVER_URL: str = Field(
        default_factory=lambda: os.getenv("AUTH_SERVER_URL", "http://localhost:8000/api/v1"),
        description="인증 서버 URL",
    )


class Settings(MongoDBSettings, APISettings, AppSettings, AuthSettings, RedisSettings):
    """모든 설정을 통합한 클래스"""

    @property
    def mongo_connection_options(self) -> Dict[str, Any]:
        """MongoDB 연결 옵션"""
        return {
            "maxPoolSize": self.max_pool_size,
            "minPoolSize": self.min_pool_size,
            "maxIdleTimeMS": 60000,
            "socketTimeoutMS": 300000,
            "connectTimeoutMS": 60000,
            "retryWrites": True,
            "waitQueueTimeoutMS": 30000,
            "waitQueueSize": 1000,
            "asyncio": True,  # PyMongo AsyncClient 사용을 위한 핵심 옵션
        }

    @classmethod
    def get_instance(cls) -> "Settings":
        """싱글턴 인스턴스 반환"""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance


# 싱글턴 패턴으로 설정 인스턴스 생성
settings = Settings.get_instance()
