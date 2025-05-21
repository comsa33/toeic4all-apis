from typing import Any, Dict, List, Optional, TypeVar

from app.db.redis_client import RedisCache
from app.services.query_service import QueryService
from app.utils.logger import logger

T = TypeVar("T")

class CachedQueryService:
    """쿼리 서비스 캐싱 래퍼"""
    
    def __init__(self):
        self.query_service = QueryService()
        
        # 각 리소스별 캐시 설정
        self.part5_cache = RedisCache("part5", default_ttl=3600)  # 1시간
        self.part6_cache = RedisCache("part6", default_ttl=3600)
        self.part7_cache = RedisCache("part7", default_ttl=3600)
        
        # 메타데이터 캐시는 더 오래 보관 (24시간)
        self.metadata_cache = RedisCache("metadata", default_ttl=86400)
    
    # Part 5 메서드
    async def get_part5_questions(self, category=None, subtype=None, difficulty=None, keyword=None, limit=10, page=1, use_cache=True):
        """Part 5 문제 조회 (캐싱 지원)"""
        if not use_cache:
            # 캐싱 무시 옵션
            return await self.query_service.get_part5_questions(category, subtype, difficulty, keyword, limit, page)
        
        # 캐시 키 생성
        cache_key = f"qs:{category}:{subtype}:{difficulty}:{keyword}:{limit}:{page}"
        
        # 캐시 확인
        cached = await self.part5_cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for Part 5 questions: {cache_key}")
            return cached
        
        # DB 조회
        questions = await self.query_service.get_part5_questions(category, subtype, difficulty, keyword, limit, page)
        
        # 캐싱 (결과가 있는 경우만)
        if questions:
            await self.part5_cache.set(cache_key, questions)
        
        return questions
    
    async def get_part5_total_count(self, category=None, subtype=None, difficulty=None, keyword=None, use_cache=True):
        """Part 5 문제 총 개수 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part5_total_count(category, subtype, difficulty, keyword)
        
        cache_key = f"count:{category}:{subtype}:{difficulty}:{keyword}"
        
        cached = await self.part5_cache.get(cache_key)
        if cached is not None:
            return cached
        
        count = await self.query_service.get_part5_total_count(category, subtype, difficulty, keyword)
        
        # 총 개수는 조금 더 오래 캐싱 (2시간)
        await self.part5_cache.set(cache_key, count, ttl=7200)
        
        return count
    
    async def get_part5_answer(self, question_id):
        """Part 5 정답 조회 (캐싱 무시 - 보안상 이유)"""
        # 정답은 캐싱하지 않음 (보안상 이유로)
        return await self.query_service.get_part5_answer(question_id)
    
    async def get_part5_categories(self, use_cache=True):
        """Part 5 카테고리 목록 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part5_used_categories()
        
        cache_key = "categories"
        
        cached = await self.metadata_cache.get(cache_key)
        if cached:
            return cached
        
        categories = await self.query_service.get_part5_used_categories()
        
        # 메타데이터는 장기간 캐싱 (24시간)
        await self.metadata_cache.set(cache_key, categories)
        
        return categories
        
    # Part 6 메서드 (유사한 패턴으로 구현)
    async def get_part6_sets(self, passage_type=None, difficulty=None, limit=2, page=1, use_cache=True):
        """Part 6 문제 세트 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part6_sets(passage_type, difficulty, limit, page)
        
        cache_key = f"sets:{passage_type}:{difficulty}:{limit}:{page}"
        
        cached = await self.part6_cache.get(cache_key)
        if cached:
            return cached
        
        sets = await self.query_service.get_part6_sets(passage_type, difficulty, limit, page)
        
        if sets:
            await self.part6_cache.set(cache_key, sets)
        
        return sets
    
    # Part 7 메서드 (유사한 패턴으로 구현)
    async def get_part7_sets(self, set_type, passage_types=None, difficulty=None, limit=1, page=1, use_cache=True):
        """Part 7 문제 세트 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part7_sets(set_type, passage_types, difficulty, limit, page)
        
        # 리스트 값을 캐시 키에 사용하기 위해 문자열로 변환
        passage_types_str = ",".join(passage_types) if passage_types else "none"
        cache_key = f"sets:{set_type}:{passage_types_str}:{difficulty}:{limit}:{page}"
        
        cached = await self.part7_cache.get(cache_key)
        if cached:
            return cached
        
        sets = await self.query_service.get_part7_sets(set_type, passage_types, difficulty, limit, page)
        
        if sets:
            await self.part7_cache.set(cache_key, sets)
        
        return sets
    
    # 캐시 관리 메서드
    async def clear_cache(self, resource_type: str = None):
        """캐시 초기화"""
        if resource_type == "part5":
            keys = await self.part5_cache.keys("*")
            for key in keys:
                await self.part5_cache.delete(key)
            return len(keys)
        elif resource_type == "part6":
            keys = await self.part6_cache.keys("*")
            for key in keys:
                await self.part6_cache.delete(key)
            return len(keys)
        elif resource_type == "part7":
            keys = await self.part7_cache.keys("*")
            for key in keys:
                await self.part7_cache.delete(key)
            return len(keys)
        elif resource_type == "metadata":
            keys = await self.metadata_cache.keys("*")
            for key in keys:
                await self.metadata_cache.delete(key)
            return len(keys)
        else:
            # 모든 캐시 삭제
            part5_count = await self.clear_cache("part5")
            part6_count = await self.clear_cache("part6")
            part7_count = await self.clear_cache("part7")
            metadata_count = await self.clear_cache("metadata")
            return part5_count + part6_count + part7_count + metadata_count
