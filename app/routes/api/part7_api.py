from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.schemas.api.part7_api_schemas import Part7AnswerResponse, Part7SetsResponse
from app.services.query_service import QueryService

router = APIRouter()
query_service = QueryService()


@router.get("/", response_model=Part7SetsResponse)
async def get_part7_sets(
    set_type: str = Query(..., description="문제 세트 유형 (Single, Double, Triple)"),
    passage_types: Optional[List[str]] = Query(None, description="지문 유형 리스트"),
    difficulty: Optional[str] = None,
    limit: int = Query(1, ge=1),
    page: int = Query(1, ge=1),
):
    """
    Part 7 문제 세트를 필터링하여 랜덤으로 조회합니다.

    - **set_type**: 문제 세트 유형 (Single, Double, Triple)
    - **passage_types**: 지문 유형 리스트 (최대 set_type에 따라 1-3개 지정 가능)
    - **difficulty**: 난이도 (Easy, Medium, Hard)
    - **limit**: 조회할 세트 수
    - **page**: 페이지 번호
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

        sets = await query_service.get_part7_sets(
            set_type, passage_types, difficulty, adjusted_limit, page
        )

        # 총 문서 수 계산 (페이지네이션용)
        total_count = await query_service.get_part7_total_count(
            set_type, passage_types, difficulty
        )

        total_pages = (total_count + adjusted_limit - 1) // adjusted_limit

        # ID 문자열 변환 처리
        for s in sets:
            s["id"] = str(s.pop("_id", None))

        return Part7SetsResponse(
            success=True,
            count=len(sets),
            total=total_count,
            page=page,
            total_pages=total_pages,
            sets=sets,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"문제 세트 조회 중 오류 발생: {str(e)}"
        )


@router.get("/{set_id}/answers/{question_seq}", response_model=Part7AnswerResponse)
async def get_part7_answer(set_id: str, question_seq: int):
    """
    Part 7 문제 세트 내 특정 문제의 정답과 해설을 조회합니다.

    - **set_id**: 문제 세트 ID
    - **question_seq**: 문제 번호(questionSeq)
    """
    try:
        answer_data = await query_service.get_part7_answer(
            ObjectId(set_id), question_seq
        )
        if not answer_data:
            raise HTTPException(status_code=404, detail="해당 문제를 찾을 수 없습니다.")

        return answer_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정답 조회 중 오류 발생: {str(e)}")


@router.get("/set_types")
async def get_set_types(used_only: bool = False):
    """
    Part 7 문제 세트 유형 목록을 반환합니다.

    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 세트 유형만 반환
    """
    if used_only:
        # 실제 사용 중인 세트 유형만 반환
        set_types_list = await query_service.get_part7_used_set_types()
        set_types = {}
        for st in set_types_list:
            set_types[st] = {
                "description": f"{st} 지문 세트",
                "required_passages": (
                    1 if st == "Single" else (2 if st == "Double" else 3)
                ),
            }
        return set_types

    # 정적 세트 유형 정보
    set_types = {
        "Single": {"description": "단일 지문 세트", "required_passages": 1},
        "Double": {"description": "이중 지문 세트", "required_passages": 2},
        "Triple": {"description": "삼중 지문 세트", "required_passages": 3},
    }
    return set_types


@router.get("/passage_types")
async def get_passage_types(set_type: Optional[str] = None, used_only: bool = False):
    """
    Part 7 지문 유형 목록을 반환합니다.

    - **set_type**: 문제 세트 유형 (Single, Double, Triple)
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 지문 유형만 반환
    """
    if used_only:
        # 실제 사용 중인 지문 유형만 반환
        return await query_service.get_part7_used_passage_types(set_type)

    # 정적 지문 유형 목록
    passage_types = [
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
    return passage_types


@router.get("/passage_combinations")
async def get_passage_combinations(set_type: str):
    """
    Part 7 지문 유형 조합 목록을 반환합니다.
    주로 Double, Triple 세트에서 자주 사용되는 지문 유형 조합을 제공합니다.

    - **set_type**: 문제 세트 유형 (Double, Triple)
    """
    if set_type not in ["Double", "Triple"]:
        return {"error": "세트 유형은 Double 또는 Triple이어야 합니다."}

    # 실제 사용 중인 지문 유형 조합 반환
    combinations = await query_service.get_part7_used_passage_combinations(set_type)

    # 조합이 없는 경우 기본 조합 제공
    if not combinations:
        if set_type == "Double":
            return [
                ["Email", "Letter"],
                ["Article", "Form"],
                ["Notice", "Memo"],
                ["Advertisement", "Email"],
            ]
        else:  # Triple
            return [
                ["Email", "Schedule", "Notice"],
                ["Chat", "Article", "Form"],
                ["Memo", "Letter", "Form"],
            ]

    return combinations


@router.get("/difficulties")
async def get_difficulties(set_type: Optional[str] = None, used_only: bool = False):
    """
    Part 7 난이도 목록을 반환합니다.

    - **set_type**: 문제 세트 유형 (Single, Double, Triple)
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 난이도만 반환
    """
    if used_only:
        # 실제 사용 중인 난이도만 반환
        return await query_service.get_part7_used_difficulties(set_type)

    # 기본 난이도 목록
    return ["Easy", "Medium", "Hard"]
