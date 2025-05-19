from typing import List, Literal

from pydantic import BaseModel, Field


class Choice(BaseModel):
    id: Literal["A", "B", "C", "D"]
    text: str
    translation: str


class VocabularyItem(BaseModel):
    word: str
    meaning: str
    partOfSpeech: str
    example: str
    exampleTranslation: str


class Part5Question(BaseModel):
    part: int = Field(5, frozen=True)
    questionCategory: Literal["문법", "어휘", "전치사/접속사/접속부사"]
    questionSubType: Literal[
        "시제",
        "수일치",
        "태(수동/능동)",
        "관계사",
        "비교구문",
        "가정법",
        "부정사/동명사",
        "동의어",
        "반의어",
        "관용표현",
        "Collocation",
        "Phrasal Verb",
        "시간/장소 전치사",
        "원인/결과",
        "양보",
        "조건",
        "접속부사",
    ]
    difficulty: Literal["Easy", "Medium", "Hard"]

    questionText: str
    questionTranslation: str

    choices: List[Choice] = Field(min_length=4, max_length=4)
    answer: Literal["A", "B", "C", "D"]

    explanation: str
    vocabulary: List[VocabularyItem] | None = None
