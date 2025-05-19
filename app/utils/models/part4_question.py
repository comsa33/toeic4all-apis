from typing import List, Literal

from pydantic import BaseModel, Field


class Speaker(BaseModel):
    country: Literal["US", "CA", "AU", "UK"]
    gender: Literal["M", "F"]


class Part4Passage(BaseModel):
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
        "주제/목적", "장소/상황", "세부사항", "추론", "의도", "화자/청자 신원"
    ]
    questionText: str
    questionTranslation: str
    choices: List[Choice] = Field(..., min_length=4, max_length=4)
    answer: Literal["A", "B", "C", "D"]
    explanation: str


class Part4Set(BaseModel):
    part: int = Field(4, frozen=True)

    passage: Part4Passage

    speaker: Speaker
    questions: List[SubQuestion] = Field(..., min_length=3, max_length=3)
