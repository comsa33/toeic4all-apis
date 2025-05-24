from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.db.redis_client import RedisCache, get_redis
from app.middleware.auth_middleware import get_current_user
from app.schemas.api.part7_api_schemas import (
    Part7AnswerResponse,
    Part7DifficultiesResponse,
    Part7PassageCombinationsResponse,
    Part7PassageTypesResponse,
    Part7SetsResponse,
    Part7SetTypesResponse,
    SetTypeInfo,
)
from app.services.cache_service import CachedQueryService

router = APIRouter(dependencies=[Depends(get_current_user)])
cached_query_service = CachedQueryService()
part7_cache = RedisCache("part7_api", default_ttl=3600)  # 1시간


@router.get("/", response_model=Part7SetsResponse)
async def get_part7_sets(
    request: Request,
    set_type: str = Query(..., description="문제 세트 유형 (Single, Double, Triple)"),
    passage_types: Optional[List[str]] = Query(None, description="지문 유형 리스트"),
    difficulty: Optional[str] = None,
    limit: int = Query(1, ge=1),
    page: int = Query(1, ge=1),
    skip_cache: bool = Query(False, description="캐시를 건너뛰고 DB에서 직접 조회"),
    redis=Depends(get_redis),
):
    """
    Part 7 문제 세트를 필터링하여 랜덤으로 조회합니다.

    - **set_type**: 문제 세트 유형 (Single, Double, Triple)
    - **passage_types**: 지문 유형 리스트 (최대 set_type에 따라 1-3개 지정 가능)
    - **difficulty**: 난이도 (Easy, Medium, Hard)
    - **limit**: 조회할 세트 수
    - **page**: 페이지 번호
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    try:
        # set_type별 최대 limit 설정
        max_limits = {"Single": 5, "Double": 2, "Triple": 2}
        adjusted_limit = min(limit, max_limits.get(set_type, 1))

        # passage_types 검증 (set_type에 맞는 개수인지)
        if passage_types and len(passage_types) > 0:
            if set_type == "Single" and len(passage_types) > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Single 세트는 최대 1개의 passage_type만 지정할 수 있습니다.",
                )
            elif set_type == "Double" and len(passage_types) > 2:
                raise HTTPException(
                    status_code=400,
                    detail="Double 세트는 최대 2개의 passage_type만 지정할 수 있습니다.",
                )
            elif set_type == "Triple" and len(passage_types) > 3:
                raise HTTPException(
                    status_code=400,
                    detail="Triple 세트는 최대 3개의 passage_type만 지정할 수 있습니다.",
                )

        # 캐시 키 생성
        passage_types_str = ",".join(passage_types) if passage_types else "none"
        cache_key = (
            f"sets:{set_type}:{passage_types_str}:{difficulty}:{adjusted_limit}:{page}"
        )

        # 캐싱된 결과 확인
        if not skip_cache:
            cached_result = await part7_cache.get(cache_key)
            if cached_result:
                return Part7SetsResponse(**cached_result)

        # 캐싱된 조회 서비스 사용
        sets = await cached_query_service.get_part7_sets(
            set_type,
            passage_types,
            difficulty,
            adjusted_limit,
            page,
            use_cache=not skip_cache,
        )

        # 총 문서 수 계산 (페이지네이션용)
        total_count = await cached_query_service.get_part7_total_count(
            set_type, passage_types, difficulty, use_cache=not skip_cache
        )

        total_pages = (total_count + adjusted_limit - 1) // adjusted_limit

        # ID 문자열 변환 처리
        for s in sets:
            if "_id" in s:
                s["id"] = str(s.pop("_id", None))

        # 응답 생성
        response = Part7SetsResponse(
            success=True,
            count=len(sets),
            total=total_count,
            page=page,
            total_pages=total_pages,
            sets=sets,
        )

        # 결과 캐싱 (비어있지 않은 경우)
        if not skip_cache and sets and len(sets) > 0:
            await part7_cache.set(cache_key, response.model_dump())

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"문제 세트 조회 중 오류 발생: {str(e)}"
        )


@router.get("/{set_id}/answers/{question_seq}", response_model=Part7AnswerResponse)
async def get_part7_answer(
    set_id: str = Path(..., description="세트 ID"),
    question_seq: int = Path(..., description="문제 번호(questionSeq)"),
    request: Request = None,
):
    """
    Part 7 문제 세트 내 특정 문제의 정답과 해설을 조회합니다.

    - **set_id**: 문제 세트 ID
    - **question_seq**: 문제 번호(questionSeq)
    """
    try:
        # 정답은 캐싱하지 않음 (보안상 이유로)
        answer_data = await cached_query_service.get_part7_answer(
            ObjectId(set_id), question_seq
        )
        if not answer_data:
            raise HTTPException(status_code=404, detail="해당 문제를 찾을 수 없습니다.")

        return answer_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정답 조회 중 오류 발생: {str(e)}")


@router.get("/set_types", response_model=Part7SetTypesResponse)
async def get_set_types(
    request: Request,
    used_only: bool = False,
    skip_cache: bool = False,
    redis=Depends(get_redis),
):
    """
    Part 7 문제 세트 유형 목록을 반환합니다.

    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 세트 유형만 반환
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    cache_key = f"set_types:{used_only}"

    # 캐싱된 결과 확인
    if not skip_cache:
        cached_result = await part7_cache.get(cache_key)
        if cached_result:
            return Part7SetTypesResponse(
                success=True,
                message="Part 7 세트 유형 목록을 성공적으로 조회했습니다.",
                data=cached_result,
            )

    if used_only:
        # 실제 사용 중인 세트 유형만 반환
        set_types_list = await cached_query_service.get_part7_used_set_types(
            use_cache=not skip_cache
        )
        set_types = {}
        for st in set_types_list:
            set_types[st] = SetTypeInfo(
                description=f"{st} 지문 세트",
                required_passages=(
                    1 if st == "Single" else (2 if st == "Double" else 3)
                ),
            )
        result = set_types
    else:
        # 정적 세트 유형 정보
        result = {
            "Single": SetTypeInfo(description="단일 지문 세트", required_passages=1),
            "Double": SetTypeInfo(description="이중 지문 세트", required_passages=2),
            "Triple": SetTypeInfo(description="삼중 지문 세트", required_passages=3),
        }

    # 결과 캐싱 (24시간)
    if not skip_cache:
        await part7_cache.set(cache_key, result, ttl=24 * 3600)

    return Part7SetTypesResponse(
        success=True,
        message="Part 7 세트 유형 목록을 성공적으로 조회했습니다.",
        data=result,
    )


@router.get("/passage_types", response_model=Part7PassageTypesResponse)
async def get_passage_types(
    request: Request,
    set_type: Optional[str] = None,
    used_only: bool = False,
    skip_cache: bool = False,
    redis=Depends(get_redis),
):
    """
    Part 7 지문 유형 목록을 반환합니다.

    - **set_type**: 문제 세트 유형 (Single, Double, Triple)
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 지문 유형만 반환
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    cache_key = f"passage_types:{set_type}:{used_only}"

    # 캐싱된 결과 확인
    if not skip_cache:
        cached_result = await part7_cache.get(cache_key)
        if cached_result:
            return Part7PassageTypesResponse(
                success=True,
                message="Part 7 지문 유형 목록을 성공적으로 조회했습니다.",
                data=cached_result,
            )

    if used_only:
        # 실제 사용 중인 지문 유형만 반환
        result = await cached_query_service.get_part7_used_passage_types(
            set_type, use_cache=not skip_cache
        )
    else:
        # 정적 지문 유형 목록
        result = [
            "Email",
            "Letter",
            "Memo",
            "Notice",
            "Advertisement",
            "Article",
            "Form",
            "Schedule",
            "Receipt",
            "Chart",
            "Chat",
            "Report",
            "Other",
        ]

    # 결과 캐싱 (24시간)
    if not skip_cache:
        await part7_cache.set(cache_key, result, ttl=24 * 3600)

    return Part7PassageTypesResponse(
        success=True,
        message="Part 7 지문 유형 목록을 성공적으로 조회했습니다.",
        data=result,
    )


@router.get("/passage_combinations", response_model=Part7PassageCombinationsResponse)
async def get_passage_combinations(
    request: Request,
    set_type: str,
    skip_cache: bool = False,
    redis=Depends(get_redis),
):
    """
    Part 7 지문 유형 조합 목록을 반환합니다.
    주로 Double, Triple 세트에서 자주 사용되는 지문 유형 조합을 제공합니다.

    - **set_type**: 문제 세트 유형 (Double, Triple)
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    if set_type not in ["Double", "Triple"]:
        raise HTTPException(
            status_code=400, detail="세트 유형은 Double 또는 Triple이어야 합니다."
        )

    cache_key = f"passage_combinations:{set_type}"

    # 캐싱된 결과 확인
    if not skip_cache:
        cached_result = await part7_cache.get(cache_key)
        if cached_result:
            return Part7PassageCombinationsResponse(
                success=True,
                message=f"Part 7 {set_type} 지문 유형 조합 목록을 성공적으로 조회했습니다.",
                data=cached_result,
            )

    # 실제 사용 중인 지문 유형 조합 반환
    combinations = await cached_query_service.get_part7_used_passage_combinations(
        set_type, use_cache=not skip_cache
    )

    # 조합이 없는 경우 기본 조합 제공
    if not combinations:
        if set_type == "Double":
            combinations = [
                ["Email", "Letter"],
                ["Article", "Form"],
                ["Notice", "Memo"],
                ["Advertisement", "Email"],
            ]
        else:  # Triple
            combinations = [
                ["Email", "Schedule", "Notice"],
                ["Chat", "Article", "Form"],
                ["Memo", "Letter", "Form"],
            ]

    # 결과 캐싱 (24시간)
    if not skip_cache:
        await part7_cache.set(cache_key, combinations, ttl=24 * 3600)

    return Part7PassageCombinationsResponse(
        success=True,
        message=f"Part 7 {set_type} 지문 유형 조합 목록을 성공적으로 조회했습니다.",
        data=combinations,
    )


@router.get("/difficulties", response_model=Part7DifficultiesResponse)
async def get_difficulties(
    request: Request,
    set_type: Optional[str] = None,
    used_only: bool = False,
    skip_cache: bool = False,
    redis=Depends(get_redis),
):
    """
    Part 7 난이도 목록을 반환합니다.

    - **set_type**: 문제 세트 유형 (Single, Double, Triple)
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 난이도만 반환
    - **skip_cache**: 캐시를 건너뛰고 DB에서 직접 조회할지 여부
    """
    cache_key = f"difficulties:{set_type}:{used_only}"

    # 캐싱된 결과 확인
    if not skip_cache:
        cached_result = await part7_cache.get(cache_key)
        if cached_result:
            return Part7DifficultiesResponse(
                success=True,
                message="Part 7 난이도 목록을 성공적으로 조회했습니다.",
                data=cached_result,
            )

    if used_only:
        # 실제 사용 중인 난이도만 반환
        result = await cached_query_service.get_part7_used_difficulties(
            set_type, use_cache=not skip_cache
        )
    else:
        # 기본 난이도 목록
        result = ["Easy", "Medium", "Hard"]

    # 결과 캐싱 (24시간)
    if not skip_cache:
        await part7_cache.set(cache_key, result, ttl=24 * 3600)

    return Part7DifficultiesResponse(
        success=True,
        message="Part 7 난이도 목록을 성공적으로 조회했습니다.",
        data=result,
    )
