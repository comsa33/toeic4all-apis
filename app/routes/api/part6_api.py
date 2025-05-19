from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.schemas.api.part6_api_schemas import Part6AnswerResponse, Part6SetsResponse
from app.services.query_service import QueryService

router = APIRouter()
query_service = QueryService()


@router.get("/", response_model=Part6SetsResponse)
async def get_part6_sets(
    passage_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = Query(2, ge=1, le=4),
    page: int = Query(1, ge=1),
):
    """
    Part 6 문제 세트를 필터링하여 랜덤으로 조회합니다.

    - **passage_type**: 지문 유형 (Email/Letter, Memo, Notice 등)
    - **difficulty**: 난이도 (Easy, Medium, Hard)
    - **limit**: 조회할 세트 수 (최대 4)
    - **page**: 페이지 번호
    """
    try:
        sets = await query_service.get_part6_sets(passage_type, difficulty, limit, page)

        # 총 문서 수 계산 (페이지네이션용)
        total_count = await query_service.get_part6_total_count(
            passage_type, difficulty
        )

        total_pages = (total_count + limit - 1) // limit

        # ID 문자열 변환 처리
        for s in sets:
            s["id"] = str(s.pop("_id", None))

        return Part6SetsResponse(
            success=True,
            count=len(sets),
            total=total_count,
            page=page,
            total_pages=total_pages,
            sets=sets,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"문제 세트 조회 중 오류 발생: {str(e)}"
        )


@router.get("/{set_id}/answers/{question_seq}", response_model=Part6AnswerResponse)
async def get_part6_answer(set_id: str, question_seq: int):
    """
    Part 6 문제 세트 내 특정 문제의 정답과 해설을 조회합니다.

    - **set_id**: 문제 세트 ID
    - **question_seq**: 문제 번호(blankNumber)
    """
    try:
        answer_data = await query_service.get_part6_answer(
            ObjectId(set_id), question_seq
        )
        if not answer_data:
            raise HTTPException(status_code=404, detail="해당 문제를 찾을 수 없습니다.")

        return answer_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정답 조회 중 오류 발생: {str(e)}")


@router.get("/passage_types")
async def get_passage_types(used_only: bool = False):
    """
    Part 6 지문 유형 목록을 반환합니다.

    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 지문 유형만 반환
    """
    if used_only:
        # 실제 사용 중인 지문 유형만 반환
        return await query_service.get_part6_used_passage_types()

    # 정적 지문 유형 목록
    passage_types = [
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
    return passage_types


@router.get("/difficulties")
async def get_difficulties(passage_type: Optional[str] = None, used_only: bool = False):
    """
    Part 6 난이도 목록을 반환합니다.

    - **passage_type**: 지문 유형 (Email/Letter, Memo, Notice 등)
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 난이도만 반환
    """
    if used_only:
        # 실제 사용 중인 난이도만 반환 (지문 유형으로 필터링 가능)
        return await query_service.get_part6_used_difficulties(passage_type)

    # 기본 난이도 목록
    return ["Easy", "Medium", "Hard"]
