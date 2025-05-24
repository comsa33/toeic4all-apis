from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.db.redis_client import RedisCache, get_redis
from app.middleware.auth_middleware import get_current_user
from app.schemas.api.part5_api_schemas import (
    Part5AnswerResponse,
    Part5CategoriesResponse,
    Part5DifficultiesResponse,
    Part5QuestionsResponse,
    Part5SubtypesResponse,
)
from app.services.cache_service import CachedQueryService

router = APIRouter(dependencies=[Depends(get_current_user)])
cached_query_service = CachedQueryService()
part5_cache = RedisCache("part5_api", default_ttl=3600)  # 1시간


@router.get("/", response_model=Part5QuestionsResponse)
async def get_part5_questions(
    request: Request,
    category: Optional[str] = None,
    subtype: Optional[str] = None,
    difficulty: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = Query(10, ge=1, le=30),
    page: int = Query(1, ge=1),
    skip_cache: bool = Query(False, description="캐시를 건너뛰고 DB에서 직접 조회"),
    redis=Depends(get_redis),
):
    """
    Part 5 문제를 필터링하여 조회합니다.

    - **category**: 문법 카테고리 (문법, 어휘, 전치사/접속사/접속부사)
    - **subtype**: 서브 카테고리 (시제, 수일치, 동의어 등)
    - **difficulty**: 난이도 (Easy, Medium, Hard)
    - **keyword**: 검색 키워드 (문제/선택지 내용)
    - **limit**: 조회할 문제 수 (최대 30)
    - **page**: 페이지 번호
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    try:
        # 캐시 키 생성
        cache_key = (
            f"questions:{category}:{subtype}:{difficulty}:{keyword}:{limit}:{page}"
        )

        # 캐싱된 결과 확인
        if not skip_cache:
            cached_result = await part5_cache.get(cache_key)
            if cached_result:
                return Part5QuestionsResponse(**cached_result)

        # 캐싱된 조회 서비스 사용
        questions = await cached_query_service.get_part5_questions(
            category,
            subtype,
            difficulty,
            keyword,
            limit,
            page,
            use_cache=not skip_cache,
        )

        # 총 문서 수 계산 (페이지네이션용)
        total_count = await cached_query_service.get_part5_total_count(
            category, subtype, difficulty, keyword, use_cache=not skip_cache
        )

        total_pages = (total_count + limit - 1) // limit

        # ID 문자열 변환 처리
        for q in questions:
            if "_id" in q:
                q["id"] = str(q.pop("_id", None))

        # 응답 생성
        response = Part5QuestionsResponse(
            success=True,
            count=len(questions),
            total=total_count,
            page=page,
            total_pages=total_pages,
            questions=questions,
        )

        # 결과 캐싱 (비어있지 않은 경우)
        if not skip_cache and questions and len(questions) > 0:
            await part5_cache.set(cache_key, response.model_dump())

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문제 조회 중 오류 발생: {str(e)}")


@router.get("/{question_id}/answer", response_model=Part5AnswerResponse)
async def get_part5_answer(
    question_id: str = Path(..., description="문제 ID"),
    request: Request = None,
):
    """
    Part 5 문제의 정답, 해설, 어휘 정보를 조회합니다.

    - **question_id**: 문제 ID
    """
    try:
        # 정답 정보는 캐싱하지 않음 (보안상 이유로)
        answer_data = await cached_query_service.get_part5_answer(ObjectId(question_id))
        if not answer_data:
            raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")

        return answer_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정답 조회 중 오류 발생: {str(e)}")


@router.get("/categories", response_model=Part5CategoriesResponse)
async def get_part5_categories(
    request: Request,
    used_only: bool = True,
    skip_cache: bool = False,
    redis=Depends(get_redis),
):
    """
    Part 5 문법 카테고리 목록을 반환합니다.

    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 카테고리만 반환
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    cache_key = f"categories:{used_only}"

    # 캐싱된 결과 확인
    if not skip_cache:
        cached_result = await part5_cache.get(cache_key)
        if cached_result:
            return Part5CategoriesResponse(
                success=True,
                message="Part 5 카테고리 목록을 성공적으로 조회했습니다.",
                data=cached_result,
            )

    if used_only:
        # 실제 사용 중인 카테고리만 반환
        categories = await cached_query_service.get_part5_categories(
            use_cache=not skip_cache
        )
    else:
        # 전체 카테고리 목록 반환
        categories = ["문법", "어휘", "전치사/접속사/접속부사"]

    # 결과 캐싱 (24시간)
    if not skip_cache:
        await part5_cache.set(cache_key, categories, ttl=24 * 3600)

    return Part5CategoriesResponse(
        success=True,
        message="Part 5 카테고리 목록을 성공적으로 조회했습니다.",
        data=categories,
    )


@router.get("/subtypes", response_model=Part5SubtypesResponse)
async def get_part5_subtypes(
    request: Request,
    category: Optional[str] = None,
    used_only: bool = True,
    skip_cache: bool = False,
    redis=Depends(get_redis),
):
    """
    Part 5 문법 서브카테고리 목록을 반환합니다.

    - **category**: 문법 카테고리 (문법, 어휘, 전치사/접속사/접속부사)
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 서브타입만 반환
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    cache_key = f"subtypes:{category}:{used_only}"

    # 캐싱된 결과 확인
    if not skip_cache:
        cached_result = await part5_cache.get(cache_key)
        if cached_result:
            return Part5SubtypesResponse(
                success=True,
                message="Part 5 서브타입 목록을 성공적으로 조회했습니다.",
                data=cached_result,
            )

    if used_only:
        # 실제 사용 중인 서브타입만 반환
        result = await cached_query_service.get_part5_subtypes(
            category, use_cache=not skip_cache
        )
    else:
        # 정적 서브타입 목록
        category_subtypes = {
            "문법": [
                "시제",
                "수일치",
                "태(수동/능동)",
                "관계사",
                "비교구문",
                "가정법",
                "부정사/동명사",
            ],
            "어휘": [
                "동의어",
                "반의어",
                "관용표현",
                "Collocation",
                "Phrasal Verb",
            ],
            "전치사/접속사/접속부사": [
                "시간/장소 전치사",
                "원인/결과",
                "양보",
                "조건",
                "접속부사",
            ],
        }

        if category:
            if category not in category_subtypes:
                result = []
            else:
                result = category_subtypes[category]
        else:
            result = category_subtypes

    # 결과 캐싱 (24시간)
    if not skip_cache:
        await part5_cache.set(cache_key, result, ttl=24 * 3600)

    return Part5SubtypesResponse(
        success=True,
        message="Part 5 서브타입 목록을 성공적으로 조회했습니다.",
        data=result,
    )


@router.get("/difficulties", response_model=Part5DifficultiesResponse)
async def get_difficulties(
    request: Request,
    category: Optional[str] = None,
    subtype: Optional[str] = None,
    used_only: bool = True,
    skip_cache: bool = False,
    redis=Depends(get_redis),
):
    """
    Part 5 난이도 목록을 반환합니다.

    - **category**: 문법 카테고리 (문법, 어휘, 전치사/접속사/접속부사)
    - **subtype**: 서브 카테고리
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 난이도만 반환
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    cache_key = f"difficulties:{category}:{subtype}:{used_only}"

    # 캐싱된 결과 확인
    if not skip_cache:
        cached_result = await part5_cache.get(cache_key)
        if cached_result:
            return Part5DifficultiesResponse(
                success=True,
                message="Part 5 난이도 목록을 성공적으로 조회했습니다.",
                data=cached_result,
            )

    if used_only:
        # 실제 사용 중인 난이도만 반환
        result = await cached_query_service.get_part5_difficulties(
            category, subtype, use_cache=not skip_cache
        )
    else:
        # 기본 난이도 목록
        result = ["Easy", "Medium", "Hard"]

    # 결과 캐싱 (24시간)
    if not skip_cache:
        await part5_cache.set(cache_key, result, ttl=24 * 3600)

    return Part5DifficultiesResponse(
        success=True,
        message="Part 5 난이도 목록을 성공적으로 조회했습니다.",
        data=result,
    )
