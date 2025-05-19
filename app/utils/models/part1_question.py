from typing import List, Literal

from pydantic import BaseModel, Field


class Speaker(BaseModel):
    country: Literal["US", "CA", "AU", "UK"]
    gender: Literal["M", "F"]


class Choice(BaseModel):
    id: Literal["A", "B", "C", "D"]
    text: str
    translation: str


class Part1Question(BaseModel):
    part: int = Field(1, frozen=True)

    # 사진·오디오
    image: str
    audio: str | None = None  # 선택 음원

    speaker: Speaker  # 4선지 모두 같은 성우
    questionType: Literal["인물 사진", "여러 인물 사진", "사물/풍경 사진"]

    choices: List[Choice] = Field(min_length=4, max_length=4)
    answer: Literal["A", "B", "C", "D"]
    explanation: str
