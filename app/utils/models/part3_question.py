from typing import List, Literal

from pydantic import BaseModel, Field


# ────────── 공통 타입 ──────────
class Speaker(BaseModel):
    id: str
    country: Literal["US", "CA", "AU", "UK"]
    gender: Literal["M", "F"]


class Part3Passage(BaseModel):
    text: str
    translation: str
    audio: str


class Choice(BaseModel):
    id: Literal["A", "B", "C", "D"]
    text: str
    translation: str


class SubQuestion(BaseModel):
    audio: str
    questionType: Literal[
        "주제/목적", "장소/상황", "화자관계", "세부사항", "추론", "의도", "시각 자료"
    ]
    questionText: str
    questionTranslation: str
    choices: List[Choice] = Field(..., min_length=4, max_length=4)
    answer: Literal["A", "B", "C", "D"]
    explanation: str


# ────────── Part 3 한 세트 ──────────
class Part3Set(BaseModel):
    part: int = Field(3, frozen=True)
    passage: Part3Passage
    speakers: List[Speaker] = Field(..., min_length=2, max_length=3)
    questions: List[SubQuestion] = Field(..., min_length=3, max_length=3)
