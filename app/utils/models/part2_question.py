from typing import List, Literal

from pydantic import BaseModel, Field


class Speaker(BaseModel):
    country: Literal["US", "CA", "AU", "UK"]
    gender: Literal["M", "F"]


class Choice(BaseModel):
    id: Literal["A", "B", "C"]
    text: str
    translation: str
    audio: str  # 보기별 음원


class Part2Question(BaseModel):
    part: int = Field(2, frozen=True)

    audio: str  # 질문 음원
    questionText: str
    questionTranslation: str

    questionType: Literal[
        "의문사 의문문",
        "일반 의문문",
        "부가 의문문",
        "선택 의문문",
        "간접 의문문",
        "평서문 질문",
        "요청/제안",
    ]

    questionSpeaker: Speaker
    answerSpeaker: Speaker

    choices: List[Choice] = Field(min_length=3, max_length=3)
    answer: Literal["A", "B", "C"]
    explanation: str
