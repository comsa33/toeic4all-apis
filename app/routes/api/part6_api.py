# app/routes/api/part6_api.py
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.db.redis_client import RedisCache, get_redis
from app.middleware.auth_middleware import get_current_user
from app.schemas.api.part6_api_schemas import (
    Part6AnswerData,
    Part6AnswerResponse,
    Part6DifficultiesResponse,
    Part6PassageTypesResponse,
    Part6SetsData,
    Part6SetsResponse,
)
from app.services.cache_service import CachedQueryService

router = APIRouter(dependencies=[Depends(get_current_user)])
cached_query_service = CachedQueryService()
part6_cache = RedisCache("part6_api", default_ttl=3600)  # 1시간


@router.get("/", response_model=Part6SetsResponse)
async def get_part6_sets(
    request: Request,
    passage_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = Query(2, ge=1, le=4),
    page: int = Query(1, ge=1),
    skip_cache: bool = Query(False, description="캐시를 건너뛰고 DB에서 직접 조회"),
    redis=Depends(get_redis),
):
    """
    Part 6 문제 세트를 필터링하여 랜덤으로 조회합니다.

    - **passage_type**: 지문 유형 (Email/Letter, Memo, Notice 등)
    - **difficulty**: 난이도 (Easy, Medium, Hard)
    - **limit**: 조회할 세트 수 (최대 4)
    - **page**: 페이지 번호
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    try:
        # 캐시 키 생성
        cache_key = f"sets:{passage_type}:{difficulty}:{limit}:{page}"

        # 캐싱된 결과 확인
        if not skip_cache:
            cached_result = await part6_cache.get(cache_key)
            if cached_result:
                return Part6SetsResponse(**cached_result)

        # 캐싱된 조회 서비스 사용
        sets = await cached_query_service.get_part6_sets(
            passage_type, difficulty, limit, page, use_cache=not skip_cache
        )

        # 총 문서 수 계산 (페이지네이션용)
        total_count = await cached_query_service.get_part6_total_count(
            passage_type, difficulty, use_cache=not skip_cache
        )

        total_pages = (total_count + limit - 1) // limit

        # ID 문자열 변환 처리
        for s in sets:
            if "_id" in s:
                s["id"] = str(s.pop("_id", None))

        # 응답 생성
        response = Part6SetsResponse(
            success=True,
            message="Part 6 문제 세트 목록을 성공적으로 조회했습니다.",
            data=Part6SetsData(sets=sets),
            count=len(sets),
            total=total_count,
            page=page,
            total_pages=total_pages,
        )

        # 결과 캐싱 (비어있지 않은 경우)
        if not skip_cache and sets and len(sets) > 0:
            await part6_cache.set(cache_key, response.model_dump())

        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"문제 세트 조회 중 오류 발생: {str(e)}"
        )


@router.get("/{set_id}/answers/{question_seq}", response_model=Part6AnswerResponse)
async def get_part6_answer(
    set_id: str = Path(..., description="세트 ID"),
    question_seq: int = Path(..., description="문제 번호(blankNumber)"),
    request: Request = None,
):
    """
    Part 6 문제 세트 내 특정 문제의 정답과 해설을 조회합니다.

    - **set_id**: 문제 세트 ID
    - **question_seq**: 문제 번호(blankNumber)
    """
    try:
        # 정답은 캐싱하지 않음 (보안상 이유로)
        answer_data = await cached_query_service.get_part6_answer(
            ObjectId(set_id), question_seq
        )
        if not answer_data:
            raise HTTPException(status_code=404, detail="해당 문제를 찾을 수 없습니다.")

        return Part6AnswerResponse(
            success=True,
            message="Part 6 정답 정보를 성공적으로 조회했습니다.",
            data=Part6AnswerData(**answer_data),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정답 조회 중 오류 발생: {str(e)}")


@router.get("/passage_types", response_model=Part6PassageTypesResponse)
async def get_passage_types(
    request: Request,
    used_only: bool = False,
    skip_cache: bool = False,
    redis=Depends(get_redis),
):
    """
    Part 6 지문 유형 목록을 반환합니다.

    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 지문 유형만 반환
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    cache_key = f"passage_types:{used_only}"

    # 캐싱된 결과 확인
    if not skip_cache:
        cached_result = await part6_cache.get(cache_key)
        if cached_result:
            return Part6PassageTypesResponse(
                success=True,
                message="Part 6 지문 유형 목록을 성공적으로 조회했습니다.",
                data=cached_result,
            )

    if used_only:
        # 실제 사용 중인 지문 유형만 반환
        result = await cached_query_service.get_part6_passage_types(
            use_cache=not skip_cache
        )
    else:
        # 정적 지문 유형 목록
        result = [
            "Email/Letter",
            "Memo",
            "Advertisement",
            "Notice",
            "Article",
            "Instruction",
            "Form",
            "Schedule",
            "Newsletter",
        ]

    # 결과 캐싱 (24시간)
    if not skip_cache:
        await part6_cache.set(cache_key, result, ttl=24 * 3600)

    return Part6PassageTypesResponse(
        success=True,
        message="Part 6 지문 유형 목록을 성공적으로 조회했습니다.",
        data=result,
    )


@router.get("/difficulties", response_model=Part6DifficultiesResponse)
async def get_difficulties(
    request: Request,
    passage_type: Optional[str] = None,
    used_only: bool = False,
    skip_cache: bool = False,
    redis=Depends(get_redis),
):
    """
    Part 6 난이도 목록을 반환합니다.

    - **passage_type**: 지문 유형 (Email/Letter, Memo, Notice 등)
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 난이도만 반환
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    cache_key = f"difficulties:{passage_type}:{used_only}"

    # 캐싱된 결과 확인
    if not skip_cache:
        cached_result = await part6_cache.get(cache_key)
        if cached_result:
            return Part6DifficultiesResponse(
                success=True,
                message="Part 6 난이도 목록을 성공적으로 조회했습니다.",
                data=cached_result,
            )

    if used_only:
        # 실제 사용 중인 난이도만 반환
        result = await cached_query_service.get_part6_difficulties(
            passage_type, use_cache=not skip_cache
        )
    else:
        # 기본 난이도 목록
        result = ["Easy", "Medium", "Hard"]

    # 결과 캐싱 (24시간)
    if not skip_cache:
        await part6_cache.set(cache_key, result, ttl=24 * 3600)

    return Part6DifficultiesResponse(
        success=True,
        message="Part 6 난이도 목록을 성공적으로 조회했습니다.",
        data=result,
    )
