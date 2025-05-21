import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union

from redis.asyncio import Redis
from fastapi import HTTPException, Request
from app.utils.logger import logger
from app.config import settings

T = TypeVar('T')

class RedisClient:
    """Redis 클라이언트 싱글톤"""
    _instance = None
    _redis: Optional[Redis] = None
    
    @classmethod
    async def get_instance(cls) -> Redis:
        """Redis 클라이언트 싱글톤 인스턴스 반환"""
        if cls._redis is None:
            redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
            cls._redis = Redis.from_url(redis_url, decode_responses=True)
            logger.info(f"Redis connection established to {redis_url}")
        return cls._redis
    
    @classmethod
    async def close(cls):
        """Redis 연결 종료"""
        if cls._redis is not None:
            await cls._redis.close()
            cls._redis = None
            logger.info("Redis connection closed")


class RedisLock:
    """Redis 기반 분산 락 관리 클래스"""
    
    def __init__(self, redis_client: Redis, lock_name: str, expire_seconds: int = 60, retry_delay: float = 0.1, retry_times: int = 50):
        self.redis = redis_client
        self.lock_name = lock_name
        self.expire_seconds = expire_seconds
        self.retry_delay = retry_delay
        self.retry_times = retry_times
        self.lock_value = None
    
    async def acquire(self, timeout: float = 10.0) -> bool:
        """락 획득을 시도합니다. 타임아웃 내에 획득하지 못하면 False 반환"""
        start_time = time.time()
        self.lock_value = str(uuid.uuid4())
        
        while time.time() - start_time < timeout:
            # SET NX (Not eXists) 옵션으로 락 획득 시도
            acquired = await self.redis.set(
                f"lock:{self.lock_name}", 
                self.lock_value, 
                ex=self.expire_seconds,  # 자동 만료 시간 설정
                nx=True
            )
            
            if acquired:
                logger.debug(f"Lock '{self.lock_name}' acquired with value '{self.lock_value}'")
                return True
                
            # 짧은 대기 후 재시도
            await asyncio.sleep(self.retry_delay)
        
        logger.warning(f"Failed to acquire lock '{self.lock_name}' after {timeout} seconds")
        return False
    
    async def release(self) -> bool:
        """락을 해제합니다. 자신이 소유한 락만 해제 가능"""
        if not self.lock_value:
            logger.warning("Attempting to release an unacquired lock")
            return False
            
        # Lua 스크립트로 원자적으로 자신의 락만 해제
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        
        # redis-py 최신 문법 사용
        result = await self.redis.eval(script, 1, f"lock:{self.lock_name}", self.lock_value)
        
        if result:
            logger.debug(f"Lock '{self.lock_name}' released")
            return True
        else:
            logger.warning(f"Failed to release lock '{self.lock_name}': not owner or expired")
            return False
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        success = await self.acquire()
        if not success:
            raise HTTPException(status_code=503, detail="서비스 일시적으로 사용 불가: 락 획득 실패")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if exc_type:
            logger.error(f"Error in context block with lock '{self.lock_name}': {exc_val}")
        await self.release()


class RedisCache(Generic[T]):
    """Redis 기반 캐싱 헬퍼 클래스"""
    
    def __init__(self, prefix: str, default_ttl: int = None):
        self.prefix = prefix
        self.default_ttl = default_ttl or int(getattr(settings, "redis_ttl", 3600))
    
    async def _get_redis(self) -> Redis:
        return await RedisClient.get_instance()
    
    def _make_key(self, key: str) -> str:
        """캐시 키 생성 (프리픽스 추가)"""
        return f"{self.prefix}:{key}"
    
    async def get(self, key: str) -> Optional[T]:
        """캐시에서 데이터 조회"""
        redis = await self._get_redis()
        data = await redis.get(self._make_key(key))
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        return None
    
    async def set(self, key: str, value: T, ttl: int = None) -> bool:
        """캐시에 데이터 저장"""
        redis = await self._get_redis()
        ttl = ttl if ttl is not None else self.default_ttl
        
        if isinstance(value, (dict, list, tuple, set, bool, int, float, str)) or value is None:
            try:
                serialized = json.dumps(value)
            except Exception:
                serialized = str(value)
        else:
            serialized = str(value)
            
        return await redis.set(self._make_key(key), serialized, ex=ttl)
    
    async def delete(self, key: str) -> bool:
        """캐시에서 데이터 삭제"""
        redis = await self._get_redis()
        return bool(await redis.delete(self._make_key(key)))
    
    async def exists(self, key: str) -> bool:
        """캐시에 키가 존재하는지 확인"""
        redis = await self._get_redis()
        return bool(await redis.exists(self._make_key(key)))
    
    async def ttl(self, key: str) -> int:
        """키의 남은 TTL 확인"""
        redis = await self._get_redis()
        return await redis.ttl(self._make_key(key))
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """특정 패턴의 모든 키 조회"""
        redis = await self._get_redis()
        full_pattern = self._make_key(pattern)
        keys = await redis.keys(full_pattern)
        # 프리픽스 제거하여 반환
        prefix_len = len(self.prefix) + 1
        return [k[prefix_len:] for k in keys]


class RateLimiter:
    """API 요청 속도 제한 클래스"""
    
    def __init__(self, prefix: str = "ratelimit", max_requests: int = 100, window_seconds: int = 60):
        self.prefix = prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def _get_redis(self) -> Redis:
        return await RedisClient.get_instance()
    
    def _make_key(self, identifier: str) -> str:
        """레이트 리미트 키 생성"""
        return f"{self.prefix}:{identifier}"
    
    async def is_allowed(self, identifier: str) -> bool:
        """요청이 허용되는지 확인"""
        redis = await self._get_redis()
        key = self._make_key(identifier)
        
        # 현재 카운트 가져오기
        count = await redis.get(key)
        
        if count is None:
            # 첫 요청이면 카운터 설정
            await redis.set(key, 1, ex=self.window_seconds)
            return True
        elif int(count) < self.max_requests:
            # 제한 내라면 카운터 증가
            await redis.incr(key)
            return True
        else:
            # 제한 초과
            return False
    
    async def get_remaining(self, identifier: str) -> Dict[str, Union[int, float]]:
        """남은 요청 수와 리셋 시간 반환"""
        redis = await self._get_redis()
        key = self._make_key(identifier)
        
        # 파이프라인으로 여러 명령 한번에 실행
        pipeline = redis.pipeline()
        pipeline.get(key)
        pipeline.ttl(key)
        results = await pipeline.execute()
        
        count = int(results[0]) if results[0] else 0
        ttl = results[1] if results[1] and results[1] > 0 else self.window_seconds
        
        return {
            "remaining": max(0, self.max_requests - count),
            "reset_seconds": ttl
        }


async def get_redis():
    """Redis 의존성 주입 함수"""
    return await RedisClient.get_instance()
