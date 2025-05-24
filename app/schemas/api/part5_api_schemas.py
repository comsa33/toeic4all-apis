# app/schemas/api/part5_api_schemas.py
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.schemas.common import BaseResponse, MetaDataResponse, PaginatedResponse


class Part5QuestionFilter(BaseModel):
    """Part 5 문제 조회 필터"""

    category: Optional[str] = Field(
        None, description="문법 카테고리 (문법, 어휘, 전치사/접속사/접속부사)"
    )
    subtype: Optional[str] = Field(None, description="서브 카테고리")
    difficulty: Optional[str] = Field(None, description="난이도 (Easy, Medium, Hard)")
    keyword: Optional[str] = Field(None, description="검색 키워드 (문제/선택지 내용)")
    limit: int = Field(10, ge=1, le=30, description="조회할 문제 수 (최대 30)")
    page: int = Field(1, ge=1, description="페이지 번호")


class Choice(BaseModel):
    """문제 선택지"""

    id: str
    text: str
    translation: str


class Part5QuestionResponse(BaseModel):
    """Part 5 문제 응답"""

    id: str
    questionCategory: str
    questionSubType: str
    difficulty: str
    questionText: str
    questionTranslation: str
    choices: List[Choice]


class Part5QuestionsData(BaseModel):
    """Part 5 문제 목록 데이터"""

    questions: List[Part5QuestionResponse]


class Part5QuestionsResponse(PaginatedResponse[Part5QuestionsData]):
    """Part 5 문제 목록 응답"""

    pass


class VocabularyItem(BaseModel):
    """어휘 정보"""

    word: str
    meaning: str
    partOfSpeech: str
    example: str
    exampleTranslation: str


class Part5AnswerData(BaseModel):
    """Part 5 정답/해설 데이터"""

    id: str
    answer: str
    explanation: str
    vocabulary: Optional[List[VocabularyItem]] = None


class Part5AnswerResponse(BaseResponse[Part5AnswerData]):
    """Part 5 정답/해설 응답"""

    pass


# 메타데이터 응답 모델들
class Part5CategoriesResponse(MetaDataResponse[List[str]]):
    """Part 5 카테고리 목록 응답"""

    pass


class Part5SubtypesResponse(MetaDataResponse[Union[List[str], Dict[str, List[str]]]]):
    """Part 5 서브타입 목록 응답"""

    pass


class Part5DifficultiesResponse(MetaDataResponse[List[str]]):
    """Part 5 난이도 목록 응답"""

    pass
