# app/schemas/api/part6_api_schemas.py
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import BaseResponse, MetaDataResponse, PaginatedResponse


class Part6Filter(BaseModel):
    """Part 6 문제 조회 필터"""

    passage_type: Optional[str] = Field(
        None, description="지문 유형 (Email/Letter, Memo, Notice 등)"
    )
    difficulty: Optional[str] = Field(None, description="난이도 (Easy, Medium, Hard)")
    limit: int = Field(2, ge=1, le=4, description="조회할 세트 수 (최대 4)")
    page: int = Field(1, ge=1, description="페이지 번호")


class Part6Choice(BaseModel):
    """선택지"""

    id: str
    text: str
    translation: str


class Part6Question(BaseModel):
    """Part 6 내 개별 문제"""

    blankNumber: int
    questionType: str
    choices: List[Part6Choice]


class Part6Set(BaseModel):
    """Part 6 문제 세트"""

    id: str
    passageType: str
    difficulty: str
    passage: str
    passageTranslation: str
    questions: List[Part6Question]


class Part6SetsData(BaseModel):
    """Part 6 문제 세트 목록 데이터"""

    sets: List[Part6Set]


class Part6SetsResponse(PaginatedResponse[Part6SetsData]):
    """Part 6 문제 세트 목록 응답"""

    pass


class Part6AnswerData(BaseModel):
    """Part 6 정답/해설 데이터"""

    set_id: str
    question_seq: int
    answer: str
    explanation: str


class Part6AnswerResponse(BaseResponse[Part6AnswerData]):
    """Part 6 정답/해설 응답"""

    pass


# 메타데이터 응답 모델들
class Part6PassageTypesResponse(MetaDataResponse[List[str]]):
    """Part 6 지문 유형 목록 응답"""

    pass


class Part6DifficultiesResponse(MetaDataResponse[List[str]]):
    """Part 6 난이도 목록 응답"""

    pass
