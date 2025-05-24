# app/schemas/api/part7_api_schemas.py
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import MetaDataResponse


class Part7Filter(BaseModel):
    """Part 7 문제 조회 필터"""

    set_type: str = Field(..., description="문제 세트 유형 (Single, Double, Triple)")
    passage_types: Optional[List[str]] = Field(None, description="지문 유형 리스트")
    difficulty: Optional[str] = Field(None, description="난이도 (Easy, Medium, Hard)")
    limit: int = Field(1, ge=1, description="조회할 세트 수")
    page: int = Field(1, ge=1, description="페이지 번호")


class Part7Choice(BaseModel):
    """선택지"""

    id: str
    text: str
    translation: str


class Part7Question(BaseModel):
    """Part 7 내 개별 문제"""

    questionSeq: int
    questionType: str
    questionText: str
    questionTranslation: str
    choices: List[Part7Choice]


class Part7Passage(BaseModel):
    """Part 7 내 개별 지문"""

    seq: int
    type: str
    text: str
    translation: str


class Part7Set(BaseModel):
    """Part 7 문제 세트"""

    id: str
    difficulty: str
    questionSetType: str
    passages: List[Part7Passage]
    questions: List[Part7Question]


class Part7SetsResponse(BaseModel):
    """Part 7 문제 세트 목록 응답"""

    success: bool = True
    count: int
    total: int
    page: int
    total_pages: int
    sets: List[Part7Set]


class Part7AnswerResponse(BaseModel):
    """Part 7 정답/해설 응답"""

    set_id: str
    question_seq: int
    answer: str
    explanation: str


# 메타데이터 응답 모델들
class SetTypeInfo(BaseModel):
    """세트 유형 정보"""

    description: str
    required_passages: int


class Part7SetTypesResponse(MetaDataResponse[Dict[str, SetTypeInfo]]):
    """Part 7 세트 유형 목록 응답"""

    pass


class Part7PassageTypesResponse(MetaDataResponse[List[str]]):
    """Part 7 지문 유형 목록 응답"""

    pass


class Part7PassageCombinationsResponse(MetaDataResponse[List[List[str]]]):
    """Part 7 지문 유형 조합 목록 응답"""

    pass


class Part7DifficultiesResponse(MetaDataResponse[List[str]]):
    """Part 7 난이도 목록 응답"""

    pass
