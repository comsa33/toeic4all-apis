# app/routes/api/part5_api.py
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, Depends

from app.schemas.api.part5_api_schemas import (
    Part5AnswerResponse,
    Part5QuestionsResponse,
)
from app.services.query_service import QueryService
from app.middleware.auth_middleware import get_current_user

router = APIRouter(
    dependencies=[Depends(get_current_user)]
)
query_service = QueryService()


@router.get("/", response_model=Part5QuestionsResponse)
async def get_part5_questions(
    category: Optional[str] = None,
    subtype: Optional[str] = None,
    difficulty: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = Query(10, ge=1, le=30),
    page: int = Query(1, ge=1),
):
    """
    Part 5 문제를 필터링하여 랜덤으로 조회합니다.

    - **category**: 문법 카테고리 (문법, 어휘, 전치사/접속사/접속부사)
    - **subtype**: 서브 카테고리 (시제, 수일치, 동의어 등)
    - **difficulty**: 난이도 (Easy, Medium, Hard)
    - **keyword**: 검색 키워드 (문제/선택지 내용)
    - **limit**: 조회할 문제 수 (최대 30)
    - **page**: 페이지 번호
    """
    try:
        questions = await query_service.get_part5_questions(
            category, subtype, difficulty, keyword, limit, page
        )

        # 총 문서 수 계산 (페이지네이션용)
        total_count = await query_service.get_part5_total_count(
            category, subtype, difficulty, keyword
        )

        total_pages = (total_count + limit - 1) // limit

        # ID 문자열 변환 처리
        for q in questions:
            q["id"] = str(q.pop("_id", None))

        return Part5QuestionsResponse(
            success=True,
            count=len(questions),
            total=total_count,
            page=page,
            total_pages=total_pages,
            questions=questions,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문제 조회 중 오류 발생: {str(e)}")


@router.get("/{question_id}/answer", response_model=Part5AnswerResponse)
async def get_part5_answer(question_id: str):
    """
    Part 5 문제의 정답, 해설, 어휘 정보를 조회합니다.

    - **question_id**: 문제 ID
    """
    try:
        answer_data = await query_service.get_part5_answer(ObjectId(question_id))
        if not answer_data:
            raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")

        return answer_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정답 조회 중 오류 발생: {str(e)}")


@router.get("/categories")
async def get_part5_categories(used_only: bool = False):
    """
    Part 5 문법 카테고리 목록을 반환합니다.

    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 카테고리만 반환
    """
    if used_only:
        # 실제 사용 중인 카테고리만 반환
        categories = await query_service.get_part5_used_categories()
    else:
        # 전체 카테고리 목록 반환
        categories = ["문법", "어휘", "전치사/접속사/접속부사"]

    return categories


@router.get("/subtypes")
async def get_part5_subtypes(category: Optional[str] = None, used_only: bool = False):
    """
    Part 5 문법 서브카테고리 목록을 반환합니다.

    - **category**: 문법 카테고리 (문법, 어휘, 전치사/접속사/접속부사)
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 서브타입만 반환
    """
    if used_only:
        # 실제 사용 중인 서브타입만 반환
        return await query_service.get_part5_used_subtypes(category)

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
            return []
        return category_subtypes[category]

    return category_subtypes


@router.get("/difficulties")
async def get_difficulties(
    category: Optional[str] = None,
    subtype: Optional[str] = None,
    used_only: bool = False,
):
    """
    Part 5 난이도 목록을 반환합니다.

    - **category**: 문법 카테고리 (문법, 어휘, 전치사/접속사/접속부사)
    - **subtype**: 서브 카테고리
    - **used_only**: True인 경우 데이터베이스에 실제 사용 중인 난이도만 반환
    """
    if used_only:
        # 실제 사용 중인 난이도만 반환
        return await query_service.get_part5_used_difficulties(category, subtype)

    # 기본 난이도 목록
    return ["Easy", "Medium", "Hard"]
