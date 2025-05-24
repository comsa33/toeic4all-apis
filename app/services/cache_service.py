from typing import TypeVar

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
    async def get_part5_questions(
        self,
        category=None,
        subtype=None,
        difficulty=None,
        keyword=None,
        limit=10,
        page=1,
        use_cache=True,
    ):
        """Part 5 문제 조회 (캐싱 지원)"""
        if not use_cache:
            # 캐싱 무시 옵션
            return await self.query_service.get_part5_questions(
                category, subtype, difficulty, keyword, limit, page
            )

        # 캐시 키 생성
        cache_key = f"qs:{category}:{subtype}:{difficulty}:{keyword}:{limit}:{page}"

        # 캐시 확인
        cached = await self.part5_cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for Part 5 questions: {cache_key}")
            return cached

        # DB 조회
        questions = await self.query_service.get_part5_questions(
            category, subtype, difficulty, keyword, limit, page
        )

        # 캐싱 (결과가 있는 경우만)
        if questions:
            await self.part5_cache.set(cache_key, questions)

        return questions

    async def get_part5_total_count(
        self, category=None, subtype=None, difficulty=None, keyword=None, use_cache=True
    ):
        """Part 5 문제 총 개수 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part5_total_count(
                category, subtype, difficulty, keyword
            )

        cache_key = f"count:{category}:{subtype}:{difficulty}:{keyword}"

        cached = await self.part5_cache.get(cache_key)
        if cached is not None:
            return cached

        count = await self.query_service.get_part5_total_count(
            category, subtype, difficulty, keyword
        )

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

    async def get_part5_subtypes(self, category=None, use_cache=True):
        """Part 5 서브타입 목록 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part5_used_subtypes(category)

        cache_key = f"subtypes:{category}"

        cached = await self.metadata_cache.get(cache_key)
        if cached:
            return cached

        subtypes = await self.query_service.get_part5_used_subtypes(category)

        # 메타데이터는 장기간 캐싱 (24시간)
        await self.metadata_cache.set(cache_key, subtypes)

        return subtypes

    async def get_part5_difficulties(self, category=None, subtype=None, use_cache=True):
        """Part 5 난이도 목록 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part5_used_difficulties(
                category, subtype
            )

        cache_key = f"difficulties:{category}:{subtype}"

        cached = await self.metadata_cache.get(cache_key)
        if cached:
            return cached

        difficulties = await self.query_service.get_part5_used_difficulties(
            category, subtype
        )

        # 메타데이터는 장기간 캐싱 (24시간)
        await self.metadata_cache.set(cache_key, difficulties)

        return difficulties

    # Part 6 메서드
    async def get_part6_sets(
        self, passage_type=None, difficulty=None, limit=2, page=1, use_cache=True
    ):
        """Part 6 문제 세트 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part6_sets(
                passage_type, difficulty, limit, page
            )

        cache_key = f"sets:{passage_type}:{difficulty}:{limit}:{page}"

        cached = await self.part6_cache.get(cache_key)
        if cached:
            return cached

        sets = await self.query_service.get_part6_sets(
            passage_type, difficulty, limit, page
        )

        if sets:
            await self.part6_cache.set(cache_key, sets)

        return sets

    async def get_part6_total_count(
        self, passage_type=None, difficulty=None, use_cache=True
    ):
        """Part 6 문제 세트 총 개수 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part6_total_count(
                passage_type, difficulty
            )

        cache_key = f"count:{passage_type}:{difficulty}"

        cached = await self.part6_cache.get(cache_key)
        if cached is not None:
            return cached

        count = await self.query_service.get_part6_total_count(passage_type, difficulty)

        # 총 개수는 조금 더 오래 캐싱 (2시간)
        await self.part6_cache.set(cache_key, count, ttl=7200)

        return count

    async def get_part6_answer(self, set_id, question_seq):
        """Part 6 정답 조회 (캐싱 무시 - 보안상 이유)"""
        # 정답은 캐싱하지 않음 (보안상 이유로)
        return await self.query_service.get_part6_answer(set_id, question_seq)

    async def get_part6_passage_types(self, use_cache=True):
        """Part 6 지문 유형 목록 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part6_used_passage_types()

        cache_key = "passage_types"

        cached = await self.metadata_cache.get(cache_key)
        if cached:
            return cached

        passage_types = await self.query_service.get_part6_used_passage_types()

        # 메타데이터는 장기간 캐싱 (24시간)
        await self.metadata_cache.set(cache_key, passage_types)

        return passage_types

    async def get_part6_difficulties(self, passage_type=None, use_cache=True):
        """Part 6 난이도 목록 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part6_used_difficulties(passage_type)

        cache_key = f"difficulties:{passage_type}"

        cached = await self.metadata_cache.get(cache_key)
        if cached:
            return cached

        difficulties = await self.query_service.get_part6_used_difficulties(
            passage_type
        )

        # 메타데이터는 장기간 캐싱 (24시간)
        await self.metadata_cache.set(cache_key, difficulties)

        return difficulties

    # Part 7 메서드
    async def get_part7_sets(
        self,
        set_type,
        passage_types=None,
        difficulty=None,
        limit=1,
        page=1,
        use_cache=True,
    ):
        """Part 7 문제 세트 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part7_sets(
                set_type, passage_types, difficulty, limit, page
            )

        # 리스트 값을 캐시 키에 사용하기 위해 문자열로 변환
        passage_types_str = ",".join(passage_types) if passage_types else "none"
        cache_key = f"sets:{set_type}:{passage_types_str}:{difficulty}:{limit}:{page}"

        cached = await self.part7_cache.get(cache_key)
        if cached:
            return cached

        sets = await self.query_service.get_part7_sets(
            set_type, passage_types, difficulty, limit, page
        )

        if sets:
            await self.part7_cache.set(cache_key, sets)

        return sets

    async def get_part7_total_count(
        self, set_type, passage_types=None, difficulty=None, use_cache=True
    ):
        """Part 7 문제 세트 총 개수 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part7_total_count(
                set_type, passage_types, difficulty
            )

        # 리스트 값을 캐시 키에 사용하기 위해 문자열로 변환
        passage_types_str = ",".join(passage_types) if passage_types else "none"
        cache_key = f"count:{set_type}:{passage_types_str}:{difficulty}"

        cached = await self.part7_cache.get(cache_key)
        if cached is not None:
            return cached

        count = await self.query_service.get_part7_total_count(
            set_type, passage_types, difficulty
        )

        # 총 개수는 조금 더 오래 캐싱 (2시간)
        await self.part7_cache.set(cache_key, count, ttl=7200)

        return count

    async def get_part7_answer(self, set_id, question_seq):
        """Part 7 정답 조회 (캐싱 무시 - 보안상 이유)"""
        # 정답은 캐싱하지 않음 (보안상 이유로)
        return await self.query_service.get_part7_answer(set_id, question_seq)

    async def get_part7_used_set_types(self, use_cache=True):
        """Part 7 세트 유형 목록 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part7_used_set_types()

        cache_key = "set_types"

        cached = await self.metadata_cache.get(cache_key)
        if cached:
            return cached

        set_types = await self.query_service.get_part7_used_set_types()

        # 메타데이터는 장기간 캐싱 (24시간)
        await self.metadata_cache.set(cache_key, set_types)

        return set_types

    async def get_part7_used_passage_types(self, set_type=None, use_cache=True):
        """Part 7 지문 유형 목록 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part7_used_passage_types(set_type)

        cache_key = f"passage_types:{set_type}"

        cached = await self.metadata_cache.get(cache_key)
        if cached:
            return cached

        passage_types = await self.query_service.get_part7_used_passage_types(set_type)

        # 메타데이터는 장기간 캐싱 (24시간)
        await self.metadata_cache.set(cache_key, passage_types)

        return passage_types

    async def get_part7_used_passage_combinations(self, set_type, use_cache=True):
        """Part 7 지문 유형 조합 목록 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part7_used_passage_combinations(
                set_type
            )

        cache_key = f"passage_combinations:{set_type}"

        cached = await self.metadata_cache.get(cache_key)
        if cached:
            return cached

        combinations = await self.query_service.get_part7_used_passage_combinations(
            set_type
        )

        # 메타데이터는 장기간 캐싱 (24시간)
        await self.metadata_cache.set(cache_key, combinations)

        return combinations

    async def get_part7_used_difficulties(self, set_type=None, use_cache=True):
        """Part 7 난이도 목록 조회 (캐싱 지원)"""
        if not use_cache:
            return await self.query_service.get_part7_used_difficulties(set_type)

        cache_key = f"difficulties:{set_type}"

        cached = await self.metadata_cache.get(cache_key)
        if cached:
            return cached

        difficulties = await self.query_service.get_part7_used_difficulties(set_type)

        # 메타데이터는 장기간 캐싱 (24시간)
        await self.metadata_cache.set(cache_key, difficulties)

        return difficulties

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
