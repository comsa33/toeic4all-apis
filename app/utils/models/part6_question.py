from typing import Annotated, List, Literal

from pydantic import BaseModel, Field

# ── 공통 타입 ──────────────────────────────────────
ChoiceID = Literal["A", "B", "C", "D"]
QuestionTP = Literal["어휘/문법", "연결어", "문장 삽입", "문장 위치"]
PassageTP = Literal[
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
BlankNo = Annotated[int, Field(ge=1, le=4)]


class Choice(BaseModel):
    id: ChoiceID
    text: str
    translation: str


class SubQuestion(BaseModel):
    blankNumber: BlankNo
    questionType: QuestionTP
    choices: List[Choice] = Field(..., min_length=4, max_length=4)
    answer: ChoiceID
    explanation: str


class Part6Set(BaseModel):
    """
    몽고DB 삽입 전 검증용 Pydantic 모델 — Part 6 세트
    필수 조건
      1. questions 배열에 4가지 questionType이 정확히 1개씩
      2. passage에 ___ 빈칸이 ‘정확히 3개’
      3. passage에 (A)(B)(C)(D) 위치 마커가 각각 1번씩
      4. blankNumber 1‧2‧3‧4가 중복 없이 존재
    """

    part: int = Field(6, frozen=True)
    difficulty: Literal["Easy", "Medium", "Hard"]
    passageType: PassageTP
    passage: str
    passageTranslation: str
    questions: List[SubQuestion] = Field(..., min_length=4, max_length=4)
